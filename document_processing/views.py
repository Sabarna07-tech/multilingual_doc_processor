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
openai.api_key = 'your-openai-api-key'

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

                # Remove the temporary file
                os.remove(temp_file_path)

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
