import google.generativeai as genai




genai.configure(api_key='AIzaSyAWXvg-3xs94Vyl6RZ0dr303UwWK57UcmQ')

categories = ["Motivation", "Planning", "Study", "Other"]

def categorize_text(text):
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"Categorize the following text into one of these categories: {categories}. Text: {text}"
    response = model.generate_content(prompt)
    return response.text.strip()

user_text = "Success is not final, failure is not fatal. It is the courage to continue that counts."
category = categorize_text(user_text)
print("Category:", category)