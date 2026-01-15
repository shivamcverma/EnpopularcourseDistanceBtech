from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import json
import re
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

PCOMBA_O_URL="https://www.shiksha.com/distance-b-e-b-tech-chp"
PCOMBA_P_URL = "https://www.shiksha.com/engineering/colleges/distance-correspondence-b-tech-colleges-india?sby=popularity&rf=filters"
PCOMBA_QN_URL = "https://www.shiksha.com/tags/b-tech-tdp-413"
PCOMBA_QND_URL = "https://www.shiksha.com/tags/b-tech-tdp-413?type=discussion"

def create_driver():
    options = Options()

    # Mandatory for GitHub Actions
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # Optional but good
    options.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Important for Ubuntu runner
    options.binary_location = "/usr/bin/chromium"

    service = Service(ChromeDriverManager().install())

    return webdriver.Chrome(
        service=service,
        options=options
    )


# ---------------- UTILITIES ----------------
def scroll_to_bottom(driver, scroll_times=3, pause=1.5):
    for _ in range(scroll_times):
        driver.execute_script("window.scrollBy(0, document.body.scrollHeight);")
        time.sleep(pause)


def extract_course_data(driver):
    driver.get(PCOMBA_O_URL)
    time.sleep(5)
    wait = WebDriverWait(driver, 15)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    data = {}

    # -------------------------------
    # Course Name
    course_name_div = soup.find("div", class_="a54c")
    if course_name_div:
        h1 = course_name_div.find("h1")
        data["title"] = h1.text.strip() if h1 else None

    # -------------------------------
    # Updated date
    updated_div = soup.find("div", string=lambda x: x and "Updated on" in x)
    if updated_div:
        span = updated_div.find("span")
        data["updated_on"] = span.text.strip() if span else None

    # -------------------------------
    # Author info
    author_block = soup.find("div", class_="be8c")
    if author_block:
        data["author"] = {
            "name": author_block.find("a").text.strip() if author_block.find("a") else None,
            "profile": author_block.find("a")["href"] if author_block.find("a") else None,
            "image": author_block.find("img")["src"] if author_block.find("img") else None,
            "role": author_block.find("span", class_="b0fc").text.strip() if author_block.find("span", class_="b0fc") else None,
            "verified": True if author_block.find("i", class_="tickIcon") else False
        }

    # =====================================================
    # OVERVIEW SECTION
    # =====================================================
    overview_div = soup.find("div", id="wikkiContents_chp_section_overview_0")
    if overview_div:

        paragraphs = []
        for p in overview_div.find_all("p")[:2]:
            text = p.get_text(" ", strip=True)
            if text and len(text) > 30:
                paragraphs.append(text)

        links = []
        for a in overview_div.find_all("a", href=True):
            links.append({
                "title": a.get_text(strip=True),
                "url": a["href"]
            })

        highlight_rows = []
        for table in overview_div.find_all("table"):
            for row in table.find_all("tr")[1:]:
                cols = row.find_all(["td", "th"])
                if len(cols) == 2:
                    highlight_rows.append({
                        "Particular": cols[0].get_text(" ", strip=True),
                        "Details": cols[1].get_text(" ", strip=True)
                    })

        data["overview"] = {
            "description": paragraphs,
            "important_links": links,
            "highlights": {
                "columns": ["Particular", "Details"],
                "rows": highlight_rows
            }
        }

    # =====================================================
    # ELIGIBILITY SECTION
    # =====================================================
    eligibility_div = soup.find("section", id="chp_section_eligibility")
    if eligibility_div:
        content = []

        # Grab all relevant elements recursively
        for elem in eligibility_div.find_all(["h1","h2","h3","h4","h5","h6","p","table","div"], recursive=True):
            if elem.name in ["h1","h2","h3","h4","h5","h6"]:
                content.append({
                    "text": elem.get_text(" ", strip=True)
                })

            elif elem.name == "table":
                headers = [th.get_text(" ", strip=True) for th in elem.find_all("th")]
                rows_data = []
                for row in elem.find_all("tr")[1:]:
                    cols = row.find_all(["td", "th"])
                    row_dict = {}
                    for idx, col in enumerate(cols):
                        key = headers[idx] if idx < len(headers) else f"col_{idx}"
                        row_dict[key] = col.get_text(" ", strip=True)
                    rows_data.append(row_dict)
                content.append({
                    "headers": headers,
                    "rows": rows_data
                })

        faq_blocks = eligibility_div.find_all("div", class_="html-0 c5db62 listener")
        for faq in faq_blocks:
            # Extract question
            question_span = faq.find("span", string=lambda x: x and x.strip().startswith("Q:"))
            question_text = None
            if question_span:
                # The actual question text is in the next span after "Q:"
                spans = faq.find_all("span")
                if len(spans) > 1:
                    question_text = spans[1].get_text(" ", strip=True)

            # Extract answer
            answer_div = faq.find_next_sibling("div", class_="_16f53f")
            answer_text = ""
            if answer_div:
                # Get all paragraph texts inside answer div
                paragraphs = answer_div.find_all("p")
                if paragraphs:
                    answer_text = " ".join(p.get_text(" ", strip=True) for p in paragraphs)
                else:
                    # Fallback: get all text inside answer div
                    answer_text = answer_div.get_text(" ", strip=True)

            if question_text and answer_text:
                content.append({
                    "question": question_text,
                    "answer": answer_text
                })

        data["eligibility_admission"] = content

    # =====================================================
    # POPULAR EXAMS & IIT SEATS
    # =====================================================
    popular_div = soup.find("div", id="wikkiContents_chp_section_popularexams_0")
    if popular_div:
        # 1. Popular Entrance Exams
        exams_table = popular_div.find("table")
        exams = []
        if exams_table:
            rows = exams_table.find_all("tr")[1:]  # skip header
            for row in rows:
                cols = row.find_all("td")
                if len(cols) == 3:
                    exams.append({
                        "exam_name": cols[0].get_text(strip=True),
                        "exam_dates": cols[1].get_text(strip=True),
                        "exam_schedule_link": cols[2].find("a")["href"] if cols[2].find("a") else None
                    })
        data["popular_exams"] = exams

        # 2. JEE Main Cutoff
        cutoff_table = popular_div.find("h3", string=lambda x: x and "JEE Main 2025 Cutoff" in x)
        cutoff_data = []
        if cutoff_table:
            table = cutoff_table.find_next("table")
            if table:
                headers = [th.get_text(strip=True) for th in table.find_all("th")]
                for row in table.find_all("tr")[1:]:
                    cols = row.find_all("td")
                    cutoff_data.append({headers[i]: cols[i].get_text(strip=True) for i in range(len(cols))})
        data["jee_main_cutoff_2025"] = cutoff_data

        # 3. IIT Seats (Delhi, Madras, Bombay)
        iit_seats = {}
        for h4 in popular_div.find_all("h4"):
            if "IIT" in h4.text and "BTech Seats" in h4.text:
                iit_name = h4.text.replace("BTech Seats","").strip()
                table = h4.find_next("table")
                seats = []
                if table:
                    headers = [th.get_text(strip=True) for th in table.find_all("th")]
                    for row in table.find_all("tr")[1:]:
                        cols = row.find_all("td")
                        seats.append({headers[i]: cols[i].get_text(strip=True) for i in range(len(cols))})
                iit_seats[iit_name] = seats
        data["iit_btech_seats"] = iit_seats

    # =====================================================
    # POPULAR SPECIALIZATIONS SECTION
    # =====================================================
    popular_specialization_div = soup.find("section", id="chp_section_popularspecialization")
    if popular_specialization_div:
        content = []
        
        # Main heading
        main_heading = popular_specialization_div.find("h2", class_="tbSec2")
        if main_heading:
            content.append({
                "text": main_heading.get_text(" ", strip=True)
            })
        
        # Introductory text
        intro_div = popular_specialization_div.find("div", class_="photo-widget-full")
        if intro_div:
            intro_text = intro_div.get_text(" ", strip=True)
            if intro_text:
                content.append({
                    "text": intro_text
                })
        
        # Specializations table
        specializations_table = popular_specialization_div.find("table")
        if specializations_table:
            # Extract table headers
            headers = [th.get_text(" ", strip=True) for th in specializations_table.find_all("th")]
            
            # Extract table rows
            rows_data = []
            for row in specializations_table.find_all("tr")[1:]:  # Skip header row
                cols = row.find_all(["td", "th"])
                row_dict = {}
                
                for idx, col in enumerate(cols):
                    key = headers[idx] if idx < len(headers) else f"col_{idx}"
                    row_dict[key] = col.get_text(" ", strip=True)
                
                rows_data.append(row_dict)
            
            content.append({
                "title": "BTech Specializations and Jobs",
                "headers": headers,
                "rows": rows_data
            })
        
        # Note text
        note_p = popular_specialization_div.find("p", string=lambda x: x and "Note" in x)
        if note_p:
            content.append({
                "text": note_p.get_text(" ", strip=True)
            })
        
        # Popular specializations list
        specialization_box = popular_specialization_div.find("div", class_="specialization-box")
        if specialization_box:
            specializations_list = []
            for li in specialization_box.find_all("li"):
                link = li.find("a", href=True)
                college_count = li.find("p")
                
                if link:
                    specializations_list.append({
                        "specialization": link.get_text(strip=True),
                        "college_count": college_count.get_text(strip=True) if college_count else None
                    })
            
            if specializations_list:
                content.append({
                    "title": "Popular Specializations by College Count",
                    "specializations": specializations_list
                })
        
        # FAQs
        faq_section = popular_specialization_div.find("div", id="sectional-faqs-0")
        if faq_section:
            faqs = []
            faq_blocks = faq_section.find_all("div", class_="html-0 c5db62 listener")
            
            for faq_block in faq_blocks:
                # Extract question
                question_spans = faq_block.find_all("span")
                question_text = None
                if len(question_spans) >= 2:
                    question_text = question_spans[1].get_text(" ", strip=True)
                
                # Extract answer from next sibling div
                answer_div = faq_block.find_next_sibling("div", class_="_16f53f")
                answer_text = ""
                if answer_div:
                    answer_content = answer_div.find("div", class_="cmsAContent")
                    if answer_content:
                        paragraphs = answer_content.find_all("p")
                        if paragraphs:
                            answer_text = " ".join(p.get_text(" ", strip=True) for p in paragraphs)
                        else:
                            answer_text = answer_content.get_text(" ", strip=True)
                
                if question_text:
                    faqs.append({
                        "question": question_text,
                        "answer": answer_text if answer_text else None
                    })
            
            if faqs:
                content.append({
                    "questions": faqs
                })
        
        # Add the entire content to data dictionary
        data["popular_specializations"] = content

    # =====================================================
    # BTECH SYLLABUS & SUBJECTS SECTION
    # =====================================================
    syllabus_div = soup.find("section", id="chp_section_coursesyllabus")
    if syllabus_div:
        content = []
        
        # Main heading
        main_heading = syllabus_div.find("h2", class_="tbSec2")
        if main_heading:
            content.append({
                "text": main_heading.get_text(" ", strip=True)
            })
        
        # Introductory text
        intro_p = syllabus_div.find("p", style="text-align: justify;")
        if intro_p:
            content.append({
                "text": intro_p.get_text(" ", strip=True)
            })
        
        # Extract all specialization syllabus sections
        specializations = []
        
        # Find all syllabus sections (CSE, Electrical, Mechanical, AI)
        syllabus_headings = syllabus_div.find_all(["h3", "h2"])
        for heading in syllabus_headings:
            heading_text = heading.get_text(" ", strip=True)
            
            # Check if this is a specialization syllabus heading
            if any(keyword in heading_text for keyword in ["BTech CSE Syllabus", "BTech Electrical Engineering Syllabus", 
                                                          "BTech Mechanical Engineering Syllabus", "BTech in Artificial Intelligence Syllabus",
                                                          "B Tech Specialization-Wise Syllabus"]):
                
                specialization_section = {
                    "title": heading_text,
                    "description": "",
                    "semester_tables": []
                }
                
                # Get description after heading
                desc_p = heading.find_next("p")
                if desc_p:
                    specialization_section["description"] = desc_p.get_text(" ", strip=True)
                
                # Get syllabus table after heading
                table = heading.find_next("table")
                if table:
                    # Extract table data without links
                    table_data = []
                    
                    # Process all rows
                    for row in table.find_all("tr"):
                        row_data = []
                        for cell in row.find_all(["td", "th"]):
                            # Get only text, remove links
                            cell_text = cell.get_text(" ", strip=True)
                            row_data.append(cell_text)
                        
                        if row_data:  # Only add non-empty rows
                            table_data.append(row_data)
                    
                    if table_data:
                        specialization_section["semester_tables"] = table_data
                
                # Add note if present
                note_p = heading.find_next("p", string=lambda x: x and "Note -" in x)
                if note_p:
                    specialization_section["note"] = note_p.get_text(" ", strip=True)
                
                specializations.append(specialization_section)
        
        # Add specialization-wise syllabus links as text only
        links_section = syllabus_div.find("h2", string=lambda x: x and "B Tech Specialization-Wise Syllabus" in x)
        if links_section:
            links_table = links_section.find_next("table")
            if links_table:
                specialization_links = []
                
                # Process all rows
                rows = links_table.find_all("tr")
                for row in rows[1:]:  # Skip header row
                    cols = row.find_all(["td", "th"])
                    if len(cols) >= 2:
                        # Get left and right column texts
                        left_text = cols[0].get_text(" ", strip=True)
                        right_text = cols[1].get_text(" ", strip=True) if len(cols) > 1 else ""
                        
                        if left_text:
                            specialization_links.append(left_text)
                        if right_text:
                            specialization_links.append(right_text)
                
                if specialization_links:
                    content.append({
                        "title": "Specialization-Wise Syllabus (Text Only)",
                        "syllabus_list": specialization_links
                    })
        
        # Useful links as text only
        useful_links_section = syllabus_div.find("p", string=lambda x: x and "Useful Link for B Tech Courses List" in x)
        if not useful_links_section:
            useful_links_section = syllabus_div.find("span", string=lambda x: x and "Useful Link for B Tech Courses List" in x)
        
        if useful_links_section:
            useful_links = []
            
            # Get the next 2 paragraphs after the heading
            next_elem = useful_links_section.find_next_sibling()
            link_count = 0
            
            while next_elem and link_count < 2:
                if next_elem.name == "p":
                    link_text = next_elem.get_text(" ", strip=True)
                    if link_text:
                        useful_links.append(link_text)
                        link_count += 1
                next_elem = next_elem.find_next_sibling()
            
            if useful_links:
                content.append({
                    "title": "Useful Information",
                    "info_items": useful_links
                })
        
        # FAQs
        faq_section = syllabus_div.find("div", id="sectional-faqs-0")
        if faq_section:
            faqs = []
            faq_blocks = faq_section.find_all("div", class_="html-0 c5db62 listener")
            
            for faq_block in faq_blocks:
                # Extract question
                question_spans = faq_block.find_all("span")
                question_text = None
                if len(question_spans) >= 2:
                    question_text = question_spans[1].get_text(" ", strip=True)
                
                # Extract answer from next sibling div
                answer_div = faq_block.find_next_sibling("div", class_="_16f53f")
                answer_text = ""
                if answer_div:
                    answer_content = answer_div.find("div", class_="cmsAContent")
                    if answer_content:
                        paragraphs = answer_content.find_all("p")
                        if paragraphs:
                            answer_text = " ".join(p.get_text(" ", strip=True) for p in paragraphs)
                        else:
                            answer_text = answer_content.get_text(" ", strip=True)
                
                if question_text:
                    faqs.append({
                        "question": question_text,
                        "answer": answer_text if answer_text else None
                    })
            
            if faqs:
                content.append({
                    "questions": faqs
                })
        
        # Add specializations to content
        if specializations:
            content.append({
                "title": "BTech Syllabus by Specialization",
                "specializations": specializations
            })
        
        # Add the entire content to data dictionary
        data["btech_syllabus"] = content

    # =====================================================
    # BTECH SALARY & CAREER SCOPE SECTION (NEW SECTION ADDED)
    # =====================================================
    salary_div = soup.find("section", id="chp_section_salary")
    if salary_div:
        content = []
        
        # Main heading
        main_heading = salary_div.find("h2", class_="tbSec2")
        if main_heading:
            content.append({
                "text": main_heading.get_text(" ", strip=True)
            })
        
        # Introductory paragraph
        intro_p = salary_div.find("p", string=lambda x: x and "BTech is one of the most popular courses" in x)
        if intro_p:
            content.append({
                "text": intro_p.get_text(" ", strip=True)
            })
        
        # B Tech Salary and Jobs in India section
        salary_jobs_heading = salary_div.find("h3", string=lambda x: x and "B Tech Salary and Jobs in India" in x)
        if salary_jobs_heading:
            salary_section = {
                "title": salary_jobs_heading.get_text(" ", strip=True),
                "description": "",
                "industry_jobs": []
            }
            
            # Get description after heading
            next_elem = salary_jobs_heading.find_next_sibling()
            description_parts = []
            while next_elem and next_elem.name != "h4":
                if next_elem.name == "p":
                    description_parts.append(next_elem.get_text(" ", strip=True))
                next_elem = next_elem.find_next_sibling()
            
            if description_parts:
                salary_section["description"] = " ".join(description_parts)
            
            content.append(salary_section)
        
        # Extract all industry job tables
        industry_sections = []
        
        # Find all industry job sections (IT & Software, Automotive, Aerospace, etc.)
        industry_headings = salary_div.find_all("h4")
        for heading in industry_headings:
            heading_text = heading.get_text(" ", strip=True)
            
            if any(keyword in heading_text for keyword in ["IT & Software", "Automotive", "Aerospace", 
                                                         "Electrical & Electronics", "Mechanical", "Civil"]):
                industry_section = {
                    "industry": heading_text.replace("B Tech Jobs", "").replace("BTech Jobs", "").strip(),
                    "description": "",
                    "job_profiles": []
                }
                
                # Get description after heading
                desc_p = heading.find_next("p")
                if desc_p:
                    industry_section["description"] = desc_p.get_text(" ", strip=True)
                
                # Get job table after heading
                table = heading.find_next("table")
                if table:
                    # Extract table headers
                    headers = []
                    header_row = table.find("tr")
                    if header_row:
                        for th in header_row.find_all(["th", "td"]):
                            headers.append(th.get_text(" ", strip=True))
                    
                    # Extract job profiles data
                    rows = table.find_all("tr")[1:]  # Skip header row
                    for row in rows:
                        cols = row.find_all(["td", "th"])
                        if len(cols) >= 3:
                            job_profile = {
                                "job_profile": cols[0].get_text(" ", strip=True),
                                "job_description": cols[1].get_text(" ", strip=True),
                                "average_salary": cols[2].get_text(" ", strip=True)
                            }
                            industry_section["job_profiles"].append(job_profile)
                
                # Add note if present
                note_p = heading.find_next("p", string=lambda x: x and "Note -" in x)
                if note_p:
                    industry_section["note"] = note_p.get_text(" ", strip=True)
                
                industry_sections.append(industry_section)
        
        # BTech Courses Top Recruiters section
        recruiters_heading = salary_div.find("h3", string=lambda x: x and "BTech Courses Top Recruiters" in x)
        if recruiters_heading:
            recruiters_section = {
                "title": recruiters_heading.get_text(" ", strip=True),
                "description": "",
                "recruiters_table": []
            }
            
            # Get description after heading
            desc_p = recruiters_heading.find_next("p")
            if desc_p:
                recruiters_section["description"] = desc_p.get_text(" ", strip=True)
            
#             # Get recruiters table
            table = recruiters_heading.find_next("table")
            if table:
                table_data = []
                rows = table.find_all("tr")
                for row in rows:
                    row_data = []
                    for cell in row.find_all(["td", "th"]):
                        row_data.append(cell.get_text(" ", strip=True))
                    if row_data:
                        table_data.append(row_data)
                
                recruiters_section["recruiters_table"] = table_data
            
            # Add note if present
            note_p = recruiters_heading.find_next("p", string=lambda x: x and "Note -" in x)
            if note_p:
                recruiters_section["note"] = note_p.get_text(" ", strip=True)
            
            content.append(recruiters_section)
        
        # BTech Placements in India section
        placements_heading = salary_div.find("h3", string=lambda x: x and "BTech Placements in India" in x)
        if placements_heading:
            placements_section = {
                "title": placements_heading.get_text(" ", strip=True),
                "description": "",
                "placements_table": []
            }
            
            # Get description after heading
            desc_p = placements_heading.find_next("p")
            if desc_p:
                placements_section["description"] = desc_p.get_text(" ", strip=True)
            
            # Get placements table
            table = placements_heading.find_next("table")
            if table:
                table_data = []
                rows = table.find_all("tr")
                for row in rows:
                    row_data = []
                    for cell in row.find_all(["td", "th"]):
                        row_data.append(cell.get_text(" ", strip=True))
                    if row_data:
                        table_data.append(row_data)
                
                placements_section["placements_table"] = table_data
            
            # Add note if present
            note_p = placements_heading.find_next("p", string=lambda x: x and "Note -" in x)
            if note_p:
                placements_section["note"] = note_p.get_text(" ", strip=True)
            
            content.append(placements_section)
        
        # Useful links as text only
        useful_links_heading = salary_div.find("p", string=lambda x: x and "Useful Links for B Tech Scope" in x)
        if not useful_links_heading:
            useful_links_heading = salary_div.find("span", string=lambda x: x and "Useful Links for B Tech Scope" in x)
        
        if useful_links_heading:
            useful_links = []
            
            # Get the next 2 paragraphs after the heading
            next_elem = useful_links_heading.find_next_sibling()
            link_count = 0
            
            while next_elem and link_count < 2:
                if next_elem.name == "p":
                    link_text = next_elem.get_text(" ", strip=True)
                    if link_text:
                        useful_links.append(link_text)
                        link_count += 1
                next_elem = next_elem.find_next_sibling()
            
            if useful_links:
                content.append({
                    "title": "Useful Links for B Tech Scope",
                    "info_items": useful_links
                })
        
        # Helpful links as text only
        helpful_links_heading = salary_div.find("p", string=lambda x: x and "Helpful Links for Jobs for BTech Freshers" in x)
        if not helpful_links_heading:
            helpful_links_heading = salary_div.find("span", string=lambda x: x and "Helpful Links for Jobs for BTech Freshers" in x)
        
        if helpful_links_heading:
            helpful_links = []
            
            # Get the next 2 paragraphs after the heading
            next_elem = helpful_links_heading.find_next_sibling()
            link_count = 0
            
            while next_elem and link_count < 2:
                if next_elem.name == "p":
                    link_text = next_elem.get_text(" ", strip=True)
                    if link_text:
                        helpful_links.append(link_text)
                        link_count += 1
                next_elem = next_elem.find_next_sibling()
            
            if helpful_links:
                content.append({
                    "title": "Helpful Links for BTech Freshers Jobs",
                    "info_items": helpful_links
                })
        
        # YouTube video iframe
        youtube_iframe = salary_div.find("iframe")
        if youtube_iframe and "youtube.com" in youtube_iframe.get("src", ""):
            content.append({
                "title": youtube_iframe.get("title", "Tips to Find Job as a Fresh BTech graduate"),
                "src": youtube_iframe["src"],
                "width": youtube_iframe.get("width", "560"),
                "height": youtube_iframe.get("height", "315")
            })
        
        # FAQs
        faq_section = salary_div.find("div", id="sectional-faqs-0")
        if faq_section:
            faqs = []
            faq_blocks = faq_section.find_all("div", class_="html-0 c5db62 listener")
            
            for faq_block in faq_blocks:
                # Extract question
                question_spans = faq_block.find_all("span")
                question_text = None
                if len(question_spans) >= 2:
                    question_text = question_spans[1].get_text(" ", strip=True)
                
                # Extract answer from next sibling div
                answer_div = faq_block.find_next_sibling("div", class_="_16f53f")
                answer_text = ""
                if answer_div:
                    answer_content = answer_div.find("div", class_="cmsAContent")
                    if answer_content:
                        paragraphs = answer_content.find_all("p")
                        if paragraphs:
                            answer_text = " ".join(p.get_text(" ", strip=True) for p in paragraphs)
                        else:
                            answer_text = answer_content.get_text(" ", strip=True)
                    
                    # Extract tables from answer if any
                    answer_tables = []
                    for table in answer_div.find_all("table"):
                        table_data = []
                        rows = table.find_all("tr")
                        for row in rows:
                            row_data = []
                            for cell in row.find_all(["td", "th"]):
                                row_data.append(cell.get_text(" ", strip=True))
                            if row_data:
                                table_data.append(row_data)
                        
                        if table_data:
                            answer_tables.append(table_data)
                
                if question_text:
                    faq_item = {
                        "question": question_text,
                        "answer": answer_text if answer_text else None
                    }
                    
                    if answer_tables:
                        faq_item["tables"] = answer_tables
                    
                    faqs.append(faq_item)
            
            if faqs:
                content.append({
                    "questions": faqs
                })
        
        # Add industry sections to content
        if industry_sections:
            content.append({
                "title": "Industry-wise BTech Jobs and Salaries",
                "industries": industry_sections
            })
        
        # Add the entire content to data dictionary
        data["btech_salary_career"] = content

    return data


def extract_popular_data(driver):
    driver.get(PCOMBA_P_URL)
    time.sleep(5)
    wait = WebDriverWait(driver, 15)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    data = {}

    main = soup.find("div", id="EdContent_categoryPage")
    if not main:
        return data

    # --------------------------------
    # Views / Count
    # --------------------------------
    views = main.find("span", class_="_2b4b")
    data["views"] = views.get_text(strip=True) if views else None

    # --------------------------------
    # Title
    # --------------------------------
    h1 = main.find("h2")
    data["title"] = h1.get_text(strip=True) if h1 else None

    # --------------------------------
    # Intro Paragraph
    # --------------------------------
    intro_p = main.find("p")
    data["intro"] = intro_p.get_text(" ", strip=True) if intro_p else None

    # --------------------------------
    # Table of Contents
    # --------------------------------
    toc = []
    toc_block = main.find("ol", class_="newTocList")
    if toc_block:
        for li in toc_block.find_all("li"):
            a = li.find("a")
            if a:
                toc.append({
                    "text": a.get_text(strip=True),
                    
                })

    data["table_of_contents"] = toc

    # --------------------------------
    # Sections (h2 based)
    # --------------------------------
    sections = []

    for h2 in main.find_all("h2"):
        section = {
        
            "heading": h2.get_text(strip=True),
            "content": []
        }

        for sibling in h2.find_next_siblings():
            if sibling.name == "h2":
                break

            # Paragraph
            if sibling.name == "p":
                section["content"].append({
                    
                    "text": sibling.get_text(" ", strip=True)
                })

            # List
            elif sibling.name == "ul":
                items = [li.get_text(" ", strip=True) for li in sibling.find_all("li")]
                section["content"].append({
                
                    "items": items
                })

            # Table
            elif sibling.name == "table":
                table_data = []
                rows = sibling.find_all("tr")

                headers = [th.get_text(strip=True) for th in rows[0].find_all("th")]

                for row in rows[1:]:
                    cols = row.find_all("td")
                    if len(cols) == len(headers):
                        row_data = {
                            headers[i]: cols[i].get_text(" ", strip=True)
                            for i in range(len(headers))
                        }
                        table_data.append(row_data)

                section["content"].append({
                   
                    "data": table_data
                })

        sections.append(section)

    data["sections"] = sections

    # --------------------------------
    # Author Info
    # --------------------------------
    author_block = main.find("div", class_="_78c3")
    if author_block:
        author_name = author_block.find("a", class_="_9b27")
        author_img = author_block.find("img")
        updated = author_block.find("p", class_="_9ad6")

        data["author"] = {
            "name": author_name.get_text(strip=True) if author_name else None,
            "profile": author_name.get("href") if author_name else None,
            "image": author_img.get("src") if author_img else None,
            "updated_on": updated.get_text(strip=True) if updated else None
        }

    return data

def scrape_shiksha_qa(driver):
    driver.get(PCOMBA_QN_URL)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.post-col[questionid][answerid][type='Q']"))
        )
    except:
        print("No Q&A blocks loaded!")
        return {}

    soup = BeautifulSoup(driver.page_source, "html.parser")

    result = {
        "tag_name": None,
        "description": None,
        "stats": {},
        "questions": []
    }

    # Optional: get tag name & description if exists
    tag_head = soup.select_one("div.tag-head")
    if tag_head:
        tag_name_el = tag_head.select_one("h1.tag-p")
        desc_el = tag_head.select_one("p.tag-bind")
        if tag_name_el:
            result["tag_name"] = tag_name_el.get_text(strip=True)
        if desc_el:
            result["description"] = desc_el.get_text(" ", strip=True)

    # Stats
    stats_cells = soup.select("div.ana-table div.ana-cell")
    stats_keys = ["Questions", "Discussions", "Active Users", "Followers"]
    for key, cell in zip(stats_keys, stats_cells):
        count_tag = cell.select_one("b")
        if count_tag:
            value = count_tag.get("valuecount") or count_tag.get_text(strip=True)
            result["stats"][key] = value

    questions_dict = {}

    for post in soup.select("div.post-col[questionid][answerid][type='Q']"):
        q_text_el = post.select_one("div.dtl-qstn .wikkiContents")
        if not q_text_el:
            continue
        question_text = q_text_el.get_text(" ", strip=True)

        # Tags
        tags = [{"tag_name": a.get_text(strip=True), "tag_url": a.get("href")}
                for a in post.select("div.ana-qstn-block .qstn-row a")]

        # Followers
        followers_el = post.select_one("span.followersCountTextArea")
        followers = int(followers_el.get("valuecount", "0")) if followers_el else 0

        # Author
        author_el = post.select_one("div.avatar-col .avatar-name")
        author_name = author_el.get_text(strip=True) if author_el else None
        author_url = author_el.get("href") if author_el else None

        # Answer text
        answer_el = post.select_one("div.avatar-col .rp-txt .wikkiContents")
        answer_text = answer_el.get_text(" ", strip=True) if answer_el else None

        # Upvotes / downvotes
        upvote_el = post.select_one("a.up-thumb.like-a")
        downvote_el = post.select_one("a.up-thumb.like-d")
        upvotes = int(upvote_el.get_text(strip=True)) if upvote_el and upvote_el.get_text(strip=True).isdigit() else 0
        downvotes = int(downvote_el.get_text(strip=True)) if downvote_el and downvote_el.get_text(strip=True).isdigit() else 0

        # Posted time (if available)
        time_el = post.select_one("div.col-head span")
        posted_time = time_el.get_text(strip=True) if time_el else None

        # Group by question
        if question_text not in questions_dict:
            questions_dict[question_text] = {
                "tags": tags,
                "followers": followers,
                "answers": []
            }
        questions_dict[question_text]["answers"].append({
            "author": {"name": author_name, "profile_url": author_url},
            "answer_text": answer_text,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "posted_time": posted_time
        })

    # Convert dict to list
    for q_text, data in questions_dict.items():
        result["questions"].append({
            "question_text": q_text,
            "tags": data["tags"],
            "followers": data["followers"],
            "answers": data["answers"]
        })

    return result


def scrape_tag_cta_D_block(driver):
    driver.get(PCOMBA_QND_URL)
    soup = BeautifulSoup(driver.page_source, "html.parser")

    result = {
        "questions": []  # store all Q&A and discussion blocks
    }

    # Scrape all Q&A and discussion blocks
    qa_blocks = soup.select("div.post-col[questionid][answerid][type='Q'], div.post-col[questionid][answerid][type='D']")
    for block in qa_blocks:
        block_type = block.get("type", "Q")
        qa_data = {
          
            "posted_time": None,
            "tags": [],
            "question_text": None,
            "followers": 0,
            "views": 0,
            "author": {
                "name": None,
                "profile_url": None,
            },
            "answer_text": None,
        }

        # Posted time
        posted_span = block.select_one("div.col-head span")
        if posted_span:
            qa_data["posted_time"] = posted_span.get_text(strip=True)

        # Tags
        tag_links = block.select("div.ana-qstn-block div.qstn-row a")
        for a in tag_links:
            qa_data["tags"].append({
                "tag_name": a.get_text(strip=True),
                "tag_url": a.get("href")
            })

        # Question / Discussion text
        question_div = block.select_one("div.dtl-qstn a div.wikkiContents")
        if question_div:
            qa_data["question_text"] = question_div.get_text(" ", strip=True)

        # Followers
        followers_span = block.select_one("span.followersCountTextArea, span.follower")
        if followers_span:
            qa_data["followers"] = int(followers_span.get("valuecount", "0"))

        # Views
        views_span = block.select_one("div.right-cl span.viewers-span")
        if views_span:
            views_text = views_span.get_text(strip=True).split()[0].replace("k","000").replace("K","000")
            try:
                qa_data["views"] = int(views_text)
            except:
                qa_data["views"] = views_text

        # Author info
        author_name_a = block.select_one("div.avatar-col a.avatar-name")
        if author_name_a:
            qa_data["author"]["name"] = author_name_a.get_text(strip=True)
            qa_data["author"]["profile_url"] = author_name_a.get("href")

        # Answer / Comment text
        answer_div = block.select_one("div.avatar-col div.wikkiContents")
        if answer_div:
            paragraphs = answer_div.find_all("p")
            if paragraphs:
                qa_data["answer_text"] = " ".join(p.get_text(" ", strip=True) for p in paragraphs)
            else:
                # Sometimes discussion/comment text is direct text without <p>
                qa_data["answer_text"] = answer_div.get_text(" ", strip=True)

        result["questions"].append(qa_data)

    return result


    
def scrape_mba_colleges():
    driver = create_driver()

      

    try:
       data = {
              "Distance_BTech":{
                   "overviews":extract_course_data(driver),
                   "popular_college":extract_popular_data(driver),
                    "QAN":{
                        "QA":scrape_shiksha_qa(driver),
                        "QAD":scrape_tag_cta_D_block(driver),
                    }
                   }
                }

    finally:
        driver.quit()
    
    return data



import os

TEMP_FILE = "popular_mba_data.tmp.json"
FINAL_FILE = "popular_mba_data.json"
UPDATE_INTERVAL = 6 * 60 * 60  # 6 hours

def auto_update_scraper():
    # Check last modified time
    # if os.path.exists(DATA_FILE):
    #     last_mod = os.path.getmtime(DATA_FILE)
    #     if time.time() - last_mod < UPDATE_INTERVAL:
    #         print("⏱️ Data is recent, no need to scrape")
    #         return

    print("🔄 Scraping started")
    data = scrape_mba_colleges()
    with open(TEMP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Atomic swap → replaces old file with new one safely
    os.replace(TEMP_FILE, FINAL_FILE)

    print("✅ Data scraped & saved successfully (atomic write)")

if __name__ == "__main__":

    auto_update_scraper()

