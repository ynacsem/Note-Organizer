import os
import shutil
import time
import pytesseract
from PIL import Image
import google.generativeai as genai
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks, HTTPException
from typing import List
from dotenv import load_dotenv
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware



# Allow requests from localhost:3000


# Load environment variables (for API key security)
load_dotenv()
GENAI_API_KEY = os.getenv("GENAI_API_KEY")

# Configure Gemini AI
genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up the main folder for organized images
MAIN_FOLDER = "Organized Notes"
os.makedirs(MAIN_FOLDER, exist_ok=True)
ZIP_PATH = "organized_notes.zip"

def cleanup_files(zip_path: str, main_folder: str):
    """
    Wait a few seconds to ensure the file has been served, then remove the ZIP file and the organized folder.
    """
    time.sleep(5)  # Delay to ensure the file is no longer in use
    if os.path.exists(zip_path):
        try:
            os.remove(zip_path)
            print(f"Removed zip file: {zip_path}")
        except Exception as e:
            print("Error removing zip file:", e)
    if os.path.exists(main_folder):
        try:
            shutil.rmtree(main_folder)
            print(f"Removed folder: {main_folder}")
        except Exception as e:
            print("Error removing folder:", e)
    # Optionally, recreate the main folder for subsequent uploads
    os.makedirs(main_folder, exist_ok=True)

@app.post("/upload/")
async def upload_file(
    file: List[UploadFile] = File(...),
    categories: List[str] = Form(...),
    background_tasks: BackgroundTasks = None
):
    """
    Uploads images, extracts text, classifies them using AI, organizes them in category folders,
    zips the organized folder, and returns the zip file for download.
    """
    results = []
    # Normalize provided categories for consistent comparison
    categories_lower = {cat.lower(): cat for cat in categories}
    print("Provided categories:", categories)

    for uploaded_file in file:
        temp_path = f"temp_{uploaded_file.filename}"
        # Save the uploaded file temporarily
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(uploaded_file.file, buffer)
        try:
            image = Image.open(temp_path)
        except Exception as e:
            os.remove(temp_path)
            results.append({"error": f"Error processing {uploaded_file.filename}: {str(e)}"})
            continue
        text = pytesseract.image_to_string(image).strip()
        # If no text is detected, remove the temp file and skip
        if not text:
            os.remove(temp_path)
            results.append({"error": f"No text detected in {uploaded_file.filename}."})
            continue

        # Build AI categorization prompt
        prompt = f"""
            Classify the following image into ONE of the given categories. Choose ONLY one category from this list: 
            {', '.join(categories)}.

            If the image does not fit into any category, respond with "Other".

            Do NOT provide explanations or multiple categories—only return the category name.

            Text extracted from image:
            {text}
            """
        try:
            response = model.generate_content(prompt)
        except Exception as e:
            os.remove(temp_path)
            results.append({"error": f"Error in AI processing for {uploaded_file.filename}: {str(e)}"})
            continue

        predicted_category = response.text.strip()
        print("AI Predicted Category:", predicted_category)
        predicted_category_lower = predicted_category.lower()
        if predicted_category_lower not in categories_lower:
            categories.append(predicted_category)
            categories_lower[predicted_category_lower] = predicted_category
            print(f"New category added: {predicted_category}")
        final_category = categories_lower[predicted_category_lower]

        # Save the file in the appropriate category folder
        category_folder = os.path.join(MAIN_FOLDER, final_category)
        os.makedirs(category_folder, exist_ok=True)
        destination_path = os.path.join(category_folder, uploaded_file.filename)
        shutil.move(temp_path, destination_path)

    # After processing all files, create the zip archive
    try:
        shutil.make_archive("organized_notes", 'zip', MAIN_FOLDER)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error creating ZIP file: " + str(e))

    # Schedule background cleanup after the response is sent
    if background_tasks is not None:
        background_tasks.add_task(cleanup_files, ZIP_PATH, MAIN_FOLDER)

    return FileResponse(ZIP_PATH, media_type="application/zip", filename="organized_notes.zip")


#python -m uvicorn file_organize:app --reload