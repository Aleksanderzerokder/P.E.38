import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import json
import re

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

SYSTEM_PROMPT = """
Ты — профессиональный ИИ-ассистент по прескорингу кандидатов.

Тебе даны: описание вакансии и резюме кандидата.

Оценивай только на основе предоставленных данных.
Не делай никаких предположений и не фантазируй, если что-то явно не указано в резюме или вакансии. Если информации нет — укажи null или 0 и прокомментируй это.

ВНИМАНИЕ: Верни результат ТОЛЬКО в формате JSON — без markdown, без текстовых комментариев, без списков, без заголовков, без пояснений.

Шаги:
1. Кратко (1–2 предложения) прокомментируй соответствие кандидата вакансии — только по фактам из резюме.
2. По каждому критерию оцени по шкале от 1 до 10 и укажи одно предложение-обоснование:
   - Hard skills
   - Релевантный опыт
   - Достижения
   - Структура резюме
   - Soft skills (оценивай только подтверждённые примерами навыки)
3. Итоговую оценку соответствия указывай строго в формате "X/10" (например, "7/10") — только строкой в кавычках. Обязательно добавь обоснование.
4. Добавь одно предложение с рекомендацией по улучшению профиля — в стиле “следующий шаг для попадания на вакансию X”.
5. Если по какому-то критерию не хватает информации — укажи это явно в обосновании и выставь 0 или null.

СТРОГО следуй структуре ниже (JSON, без изменений, только такой формат Total_score):

{
  "Комментарий": "...",
  "Hard_skills": 0,
  "Обоснование_Hard_skills": "...",
  "Relevant_experience": 0,
  "Обоснование_Relevant_experience": "...",
  "Achievements": 0,
  "Обоснование_Achievements": "...",
  "Resume_structure": 0,
  "Обоснование_Resume_structure": "...",
  "Soft_skills": 0,
  "Обоснование_Soft_skills": "...",
  "Total_score": "0/10",
  "Обоснование_итога": "...",
  "Recommendations": "..."
}

Ответь только этим JSON! Никаких пояснений, markdown, текстов вне JSON!

Если не можешь заполнить какое-то поле — ставь 0 или null и объясняй причину только внутри соответствующего поля.
"""

def get_html(url: str) -> str:
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        st.error(f"Ошибка при загрузке {url}: {e}")
        return ""

def extract_vacancy_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    desc = soup.find("div", {"data-qa": "vacancy-description"})
    if desc:
        return desc.get_text(separator="\n", strip=True)
    return soup.get_text(separator="\n", strip=True)

def extract_resume_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    desc = soup.find("div", {"class": "resume-applicant-main-info"})
    if desc:
        return desc.get_text(separator="\n", strip=True)
    return soup.get_text(separator="\n", strip=True)

def request_gpt(system_prompt, user_prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=1200,
        temperature=0,
    )
    return response.choices[0].message.content

st.title("ИИ-ассистент прескоринга по ссылкам")

vacancy_url = st.text_input("Ссылка на вакансию (hh.ru, SuperJob и др.)")
resume_url = st.text_input("Ссылка на резюме (hh.ru, SuperJob и др.)")

if st.button("Оценить по ссылкам"):
    with st.spinner("Скачиваем данные..."):
        job_desc_html = get_html(vacancy_url)
        cv_html = get_html(resume_url)
        if job_desc_html and cv_html:
            job_description = extract_vacancy_text(job_desc_html)
            cv = extract_resume_text(cv_html)
            user_prompt = f"# Вакансия\n{job_description}\n\n# Резюме\n{cv}"
            response = request_gpt(SYSTEM_PROMPT, user_prompt)
            st.subheader("Результат (JSON):")
            st.code(response, language="json")
            try:
                result = json.loads(response)
                total_score = result.get("Total_score", "")
                if not re.match(r'^\d{1,2}/10$', str(total_score)):
                    st.error(f"Итоговая оценка Total_score имеет неправильный формат: '{total_score}'. Должно быть, например, '7/10'. Проверь промт.")
                else:
                    st.subheader("Результаты оценки:")
                    for k, v in result.items():
                        st.write(f"**{k}**: {v}")
            except Exception:
                st.error("⚠️ Не удалось преобразовать результат в JSON. Проверь промт или входные данные.")
        else:
            st.error("Не удалось получить текст вакансии или резюме по ссылке. Проверьте URL или попробуйте скопировать данные вручную.")

st.caption("v1.0 | Автоматический парсинг по ссылкам. Powered by OpenAI & Streamlit")

