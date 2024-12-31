from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from .forms import DocumentForm
from .models import Document, QuestionAnswer
from PyPDF2 import PdfReader
from pytesseract import pytesseract
from PIL import Image
from langdetect import detect
from googletrans import Translator
from sentence_transformers import SentenceTransformer
import faiss
import os
import openai

# Initialize FAISS and SentenceTransformer
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
index = faiss.IndexFlatL2(384)  # Dimension of embeddings for 'all-MiniLM-L6-v2'
documents = []  # To store extracted text chunks

# OpenAI API Key
openai.api_key = 'your-openai-api-key'

# Helper functions
def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    return "".join(page.extract_text() for page in reader.pages)

def extract_text_from_image(file_path):
    image = Image.open(file_path)
    return pytesseract.image_to_string(image)

def process_uploaded_file(uploaded_file):
    file_extension = os.path.splitext(uploaded_file.name)[1].lower()
    temp_file_path = f"temp/{uploaded_file.name}"

    with open(temp_file_path, 'wb') as temp_file:
        for chunk in uploaded_file.chunks():
            temp_file.write(chunk)

    processed_text = None
    if file_extension == '.pdf':
        processed_text = extract_text_from_pdf(temp_file_path)
    elif file_extension in ['.jpg', '.jpeg', '.png']:
        processed_text = extract_text_from_image(temp_file_path)

    os.remove(temp_file_path)
    return processed_text

def index_text_chunks(text):
    global index, documents
    chunks = [text[i:i+500] for i in range(0, len(text), 500)]
    documents.extend(chunks)
    embeddings = embedding_model.encode(chunks, convert_to_tensor=False)
    index.add(embeddings)

def query_rag(question):
    global index, documents
    question_embedding = embedding_model.encode([question], convert_to_tensor=False)
    _, indices = index.search(question_embedding, 3)
    relevant_chunks = [documents[i] for i in indices[0]]
    context = "\n".join(relevant_chunks)
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=f"Context:\n{context}\n\nQuestion: {question}\nAnswer:",
        max_tokens=150
    )
    return response['choices'][0]['text'].strip()

# Views
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def upload_document(request):
    processed_text = None
    language = None
    translated_text = None
    answer = None

    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        question = request.POST.get('question')
        
        if form.is_valid() or question:
            if not question:
                uploaded_file = request.FILES['file']
                processed_text = process_uploaded_file(uploaded_file)

                if processed_text:
                    language = detect(processed_text)
                    translator = Translator()
                    translated_text = translator.translate(processed_text, src=language, dest='en').text
                    index_text_chunks(translated_text)

                    Document.objects.create(
                        user=request.user,
                        file_name=uploaded_file.name,
                        text=processed_text,
                        translated_text=translated_text,
                        language=language
                    )
            else:
                answer = query_rag(question)

                if request.user.is_authenticated:
                    document = Document.objects.filter(user=request.user).last()
                    QuestionAnswer.objects.create(
                        user=request.user,
                        document=document,
                        question=question,
                        answer=answer
                    )
    else:
        form = DocumentForm()

    return render(request, 'document_processing/result.html', {
        'form': form,
        'processed_text': processed_text,
        'language': language,
        'translated_text': translated_text,
        'answer': answer
    })

@login_required
def dashboard(request):
    documents = Document.objects.filter(user=request.user)
    return render(request, 'document_processing/dashboard.html', {'documents': documents})

@login_required
def export_document(request, document_id):
    try:
        document = Document.objects.get(id=document_id, user=request.user)
    except Document.DoesNotExist:
        return HttpResponse("Document not found.", status=404)

    response = HttpResponse(content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="{document.file_name}.txt"'
    response.write(f"File Name: {document.file_name}\n")
    response.write(f"Uploaded At: {document.uploaded_at}\n")
    response.write(f"Language: {document.language}\n")
    response.write("\nExtracted Text:\n")
    response.write(document.text or "No extracted text available.\n")
    response.write("\nTranslated Text:\n")
    response.write(document.translated_text or "No translated text available.\n")
    return response
