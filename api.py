from fastapi import FastAPI, HTTPException
import json, os
from datetime import datetime

app = FastAPI(title="MBA popular course")

DATA_FILE = "popular_mba_data.json"


def load_data():
    if not os.path.exists(DATA_FILE):
        raise HTTPException(
            status_code=503,
            detail="Data not generated yet. Please wait."
        )

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


# 🔍 Recursive function to find section by name
def find_section(data, section_name):
    if isinstance(data, dict):
        for key, value in data.items():
            if key.lower() == section_name.lower():
                return value
            result = find_section(value, section_name)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_section(item, section_name)
            if result is not None:
                return result
    return None


@app.get("/")
def root():
    return {
        "status": "API running 🚀",
        "source": "GitHub Actions Auto Scraper"
    }


# 🔹 Full data
@app.get("/Distance_btech_popular_course_BE_Btech")
def get_all_data():
    return {
        "data": load_data()
    }


# 🔹 Access ANY section by name
@app.get("/Distance_btech_popular_course/{section_name}")
def get_section_by_name(section_name: str):
    data = load_data()
    result = find_section(data, section_name)

    if result is None:
        raise HTTPException(status_code=404, detail="Section not found")

    return {
        "section": section_name,
        "data": result
    }