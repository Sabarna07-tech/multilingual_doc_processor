# document_processing/views.py

from django.shortcuts import render
from django.utils.translation import gettext as _
from .forms import DocumentForm

def upload_document(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            # Handle file processing here
            context = {
                'message': _('File uploaded successfully'),
                # Add other context variables here
            }
            return render(request, 'document_processing/result.html', context)
    else:
        form = DocumentForm()
    return render(request, 'document_processing/upload.html', {'form': form})
import os
from django.shortcuts import render
from django.utils.translation import gettext as _
from .forms import DocumentForm
from PyPDF2 import PdfReader
from pytesseract import pytesseract
from PIL import Image
from langdetect import detect
from googletrans import Translator

def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_image(file_path):
    image = Image.open(file_path)
    return pytesseract.image_to_string(image)

def upload_document(request):
    processed_text = None
    language = None
    translated_text = None

    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()

            # Save the uploaded file temporarily
            temp_file_path = f"temp/{uploaded_file.name}"
            with open(temp_file_path, 'wb') as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)

            # Extract text based on file type
            if file_extension == '.pdf':
                processed_text = extract_text_from_pdf(temp_file_path)
            elif file_extension in ['.jpg', '.jpeg', '.png']:
                processed_text = extract_text_from_image(temp_file_path)

            # Detect language
            if processed_text:
                language = detect(processed_text)

                # Translate text
                translator = Translator()
                translated_text = translator.translate(processed_text, src=language, dest='en').text

            # Remove the temporary file
            os.remove(temp_file_path)

    else:
        form = DocumentForm()

    return render(request, 'document_processing/result.html', {
        'form': form,
        'processed_text': processed_text,
        'language': language,
        'translated_text': translated_text
    })
import os
from django.shortcuts import render
from django.utils.translation import gettext as _
from .forms import DocumentForm
from PyPDF2 import PdfReader
from pytesseract import pytesseract
from PIL import Image
from langdetect import detect
from googletrans import Translator
from sentence_transformers import SentenceTransformer
import faiss
import openai

# Initialize FAISS and SentenceTransformer
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
index = faiss.IndexFlatL2(384)  # Dimension of embeddings for 'all-MiniLM-L6-v2'
documents = []  # To store extracted text chunks

# OpenAI API Key
openai.api_key = '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'

def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_image(file_path):
    image = Image.open(file_path)
    return pytesseract.image_to_string(image)

def index_text_chunks(text):
    global index, documents
    # Split the text into smaller chunks
    chunks = [text[i:i+500] for i in range(0, len(text), 500)]
    documents.extend(chunks)

    # Create embeddings for the chunks
    embeddings = embedding_model.encode(chunks, convert_to_tensor=False)
    index.add(embeddings)  # Add embeddings to the FAISS index

def query_rag(question):
    global index, documents

    # Create the embedding for the question
    question_embedding = embedding_model.encode([question], convert_to_tensor=False)

    # Retrieve the top 3 most relevant chunks
    _, indices = index.search(question_embedding, 3)
    relevant_chunks = [documents[i] for i in indices[0]]

    # Combine the retrieved chunks into context
    context = "\n".join(relevant_chunks)

    # Use OpenAI GPT to generate an answer based on the context
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=f"Context:\n{context}\n\nQuestion: {question}\nAnswer:",
        max_tokens=150
    )
    return response['choices'][0]['text'].strip()

def process_uploaded_file(uploaded_file):
    file_extension = os.path.splitext(uploaded_file.name)[1].lower()
    
    # Save the uploaded file temporarily
    temp_file_path = f"temp/{uploaded_file.name}"
    with open(temp_file_path, 'wb') as temp_file:
        for chunk in uploaded_file.chunks():
            temp_file.write(chunk)

    # Extract text based on file type
    if file_extension == '.pdf':
        processed_text = extract_text_from_pdf(temp_file_path)
    elif file_extension in ['.jpg', '.jpeg', '.png']:
        processed_text = extract_text_from_image(temp_file_path)
    else:
        processed_text = None

    # Remove the temporary file
    os.remove(temp_file_path)

    return processed_text

def upload_document(request):
    processed_text = None
    language = None
    translated_text = None
    answer = None

    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        question = request.POST.get('question')  # Get the question from the form
        if form.is_valid() or question:
            if not question:  # If uploading a document
                uploaded_file = request.FILES['file']
                processed_text = process_uploaded_file(uploaded_file)

                # Detect language
                if processed_text:
                    language = detect(processed_text)

                    # Translate text
                    translator = Translator()
                    translated_text = translator.translate(processed_text, src=language, dest='en').text

                    # Index the translated text
                    index_text_chunks(translated_text)

            else:  # If asking a question
                answer = query_rag(question)

    else:
        form = DocumentForm()

    return render(request, 'document_processing/result.html', {
        'form': form,
        'processed_text': processed_text,
        'language': language,
        'translated_text': translated_text,
        'answer': answer
    })
    from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})
from .models import Document, QuestionAnswer
from django.contrib.auth.decorators import login_required

@login_required
def upload_document(request):
    processed_text = None
    language = None
    translated_text = None
    answer = None

    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        question = request.POST.get('question')  # Get the question from the form
        if form.is_valid() or question:
            if not question:  # If uploading a document
                uploaded_file = request.FILES['file']
                file_extension = os.path.splitext(uploaded_file.name)[1].lower()

                # Save the uploaded file temporarily
                temp_file_path = f"temp/{uploaded_file.name}"
                with open(temp_file_path, 'wb') as temp_file:
                    for chunk in uploaded_file.chunks():
                        temp_file.write(chunk)

                # Extract text based on file type
                if file_extension == '.pdf':
                    processed_text = extract_text_from_pdf(temp_file_path)
                elif file_extension in ['.jpg', '.jpeg', '.png']:
                    processed_text = extract_text_from_image(temp_file_path)

                # Detect language
                if processed_text:
                    language = detect(processed_text)

                    # Translate text
                    translator = Translator()
                    translated_text = translator.translate(processed_text, src=language, dest='en').text

                    # Index the translated text
                    index_text_chunks(translated_text)

                    # Save the document in the database
                    document = Document.objects.create(
                        user=request.user,
                        file_name=uploaded_file.name,
                        text=processed_text,
                        translated_text=translated_text,
                        language=language
                    )

                # Remove the temporary file
                os.remove(temp_file_path)

            else:  # If asking a question
                question = request.POST.get('question')
                answer = query_rag(question)

                # Log the question and answer in the database
                if request.user.is_authenticated:
                    document = Document.objects.filter(user=request.user).last()  # Get the latest document
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
from django.contrib.auth.decorators import login_required
from .models import Document

@login_required
def dashboard(request):
    # Fetch documents uploaded by the logged-in user
    documents = Document.objects.filter(user=request.user)
    return render(request, 'document_processing/dashboard.html', {'documents': documents})
from django.http import HttpResponse
import csv

@login_required
def export_document(request, document_id):
    try:
        document = Document.objects.get(id=document_id, user=request.user)
    except Document.DoesNotExist:
        return HttpResponse("Document not found.", status=404)

    # Create a response object for the file download
    response = HttpResponse(content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="{document.file_name}.txt"'

    # Write the document content to the response
    response.write(f"File Name: {document.file_name}\n")
    response.write(f"Uploaded At: {document.uploaded_at}\n")
    response.write(f"Language: {document.language}\n")
    response.write("\nExtracted Text:\n")
    response.write(document.text or "No extracted text available.\n")
    response.write("\nTranslated Text:\n")
    response.write(document.translated_text or "No translated text available.\n")

    return response
