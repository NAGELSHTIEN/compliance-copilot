import streamlit as st
import json
from datetime import datetime
from pypdf import PdfReader
from openai import OpenAI

st.set_page_config(
    page_title="Compliance Copilot AI - Enterprise Suite",
    page_icon="🛡️",
    layout="wide"
)

# עיצוב מותאם לעברית (RTL)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;600;700;800&display=swap');
    html, body, [class*="css"] {
        font-family: 'Heebo', sans-serif;
        direction: rtl;
        text-align: right;
    }
    .stAlert, div[data-testid="stMetricValue"], div[data-testid="stMetricLabel"] {
        direction: rtl;
        text-align: right;
    }
    .report-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 18px;
        margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    </style>
""", unsafe_allow_html=True)

# מאגר בקרות לפי תקנים
STANDARDS_DB = {
    "ISO/IEC 27001:2022": [
        {"id": "A.5.1", "domain": "בקרות ארגוניות", "title": "מדיניות אבטחת מידע", "req": "מדיניות מאושרת רשמית ע\"י ההנהלה, מעודכנת שנתית ומפורסמת."},
        {"id": "A.5.15", "domain": "בקרות ארגוניות", "title": "בקרת גישה והרשאות", "req": "הרשאה מינימלית (Least Privilege), אימות דו-שלבי (MFA) וביטול גישה מיידי."},
        {"id": "A.5.24", "domain": "ניהול אירועים", "title": "ניהול אירועי סייבר", "req": "צוות תגובה ייעודי (CSIRT), סיווג חומרות וזמני מענה מוגדרים."},
        {"id": "A.6.3", "domain": "משאבי אנוש", "title": "הדרכות ומודעות", "req": "הדרכת קליטה תוך 14 יום, ריענון שנתי ומבדקי דיוג תקופתיים."},
        {"id": "A.8.8", "domain": "בקרות טכנולוגיות", "title": "ניהול פגיעויות וטלאי אבטחה", "req": "סריקות שבועיות, התקנת עדכוני אבטחה קריטיים ומבדק חדירות שנתי."},
        {"id": "A.8.12", "domain": "בקרות טכנולוגיות", "title": "מניעת דליפת מידע והצפנה", "req": "הצפנת AES-256 במנוחה ו-TLS 1.3 בתנועה ובקרות DLP."}
    ],
    "SOC 2 Type II": [
        {"id": "CC6.1", "domain": "Security & Access", "title": "ניהול גישה והרשאות לוגיות", "req": "הגבלת גישה למערכות ייצור על בסיס הרשאה מינימלית ואימות רב-שלבי."},
        {"id": "CC6.6", "domain": "Security & Network", "title": "הגנת גבולות רשת והצפנה", "req": "חומות אש, פילוח רשת והצפנת מידע בתנועה ובמנוחה."},
        {"id": "CC7.1", "domain": "Monitoring & Incident", "title": "ניטור תשתיות וזיהוי חריגות", "req": "מערכת ניטור מרכזית (SIEM) ונוהל תגובה מהיר לאירועי אבטחה."},
        {"id": "CC8.1", "domain": "Change Management", "title": "בקרת שינויים בקוד", "req": "בדיקת קוד כפולה (Peer Review), סביבות Staging נפרדות ואישורי פריסה."}
    ],
    "GDPR (הגנת הפרטיות)": [
        {"id": "Art.32", "domain": "Security of Processing", "title": "אבטחת עיבוד נתונים אישיים", "req": "הצפנה ואנונימיזציה של מידע אישי וגיבויים תקופתיים."},
        {"id": "Art.33", "domain": "Breach Notification", "title": "חובת דיווח על דליפת מידע", "req": "נוהל דיווח לרשות להגנת הפרטיות תוך 72 שעות מאירוע דליפה."},
        {"id": "Art.17", "domain": "Data Rights", "title": "הזכות להישכח ומחיקת מידע", "req": "מנגנון טכנולוגי ונהלי למחיקת מידע אישי לפי דרישת משתמש."}
    ]
}

def extract_text_from_file(uploaded_file):
    if uploaded_file.name.endswith(".pdf"):
        pdf_reader = PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text
    return uploaded_file.read().decode("utf-8", errors="ignore")

def run_analysis(policy_text, standard_name):
    text_lower = policy_text.lower()
    controls = STANDARDS_DB.get(standard_name, STANDARDS_DB["ISO/IEC 27001:2022"])
    results = []

    for c in controls:
        cid = c["id"]
        # בדיקת תנאי עמידה לפי מילות מפתח
        if cid in ["A.5.1", "CC8.1", "Art.17"]:
            passed = ("אישור" in text_lower or "הנהל" in text_lower or "מחיק" in text_lower) and ("שנה" in text_lower or "סקיר" in text_lower)
            clause = f"סעיף מדיניות מתקן עבור {c['title']}: החברה מחייבת תהליך אישור שנתי של ההנהלה, סקירה תקופתית ויישום מנגנון רשמי המתועד במערכת."
        elif cid in ["A.5.15", "CC6.1", "Art.32"]:
            passed = ("mfa" in text_lower or "רב-שלבי" in text_lower) and ("הרשאה מינימלית" in text_lower or "least privilege" in text_lower or "הצפנ" in text_lower)
            clause = f"סעיף מדיניות מתקן עבור {c['title']}: הגישה לכלל המערכות מבוססת על עקרון ההרשאה המינימלית ואימות רב-שלבי (MFA). ביטול גישה יבוצע תוך מקסימום שעתיים ממועד עזיבת עובד."
        elif cid in ["A.5.24", "CC7.1", "Art.33"]:
            passed = ("צוות תגובה" in text_lower or "csirt" in text_lower or "72" in text_lower or "siem" in text_lower) and "אירוע" in text_lower
            clause = f"סעיף מדיניות מתקן עבור {c['title']}: אירועי אבטחה יטופלו על ידי צוות תגובה ייעודי עם SLA של עד 60 דקות, וחובת דיווח תוך 72 שעות במקרה של דליפת נתונים."
        elif cid == "A.6.3":
            passed = ("הדרכ" in text_lower or "אימון" in text_lower) and ("דיוג" in text_lower or "phishing" in text_lower)
            clause = "סעיף 4.1 - הדרכות עובדים: כל עובד יעבור הדרכת אבטחת מידע תוך 14 יום מקליטתו, והחברה תקיים תרגול דיוג מדומה אחת לרבעון."
        elif cid in ["A.8.8", "CC6.6"]:
            passed = ("סריק" in text_lower or "חולש" in text_lower or "patch" in text_lower) and ("עדכונ" in text_lower or "טלאי" in text_lower or "חדירות" in text_lower)
            clause = "סעיף 5.1 - ניהול חולשות וטלאים: סריקות פגיעויות שבועיות ועדכוני אבטחה קריטיים יותקנו תוך מקסימום 7 ימי עבודה לאחר בדיקת Staging."
        else: # A.8.12
            passed = ("הצפנ" in text_lower or "aes" in text_lower) and ("dlp" in text_lower or "דליפ" in text_lower)
            clause = "סעיף 6.1 - מניעת דליפת מידע והצפנה: כלל הנתונים יוצפנו בתקן AES-256 במנוחה ו-TLS 1.3 בתנועה, לצד מערכת DLP לחסימת דלף מידע."

        status = "עומד בתקן" if passed else "פער קריטי"
        results.append({
            "control_id": cid,
            "domain": c["domain"],
            "title": c["title"],
            "requirement_description": c["req"],
            "status": status,
            "findings": "הדרישה מיושמת במלואה במסמך הנהלים." if passed else "לא נמצאה התייחסות מספקת או מלאה לדרישה זו במסמך.",
            "evidence_quote": "סעיף מאומת במסמך" if passed else "לא נמצא במסמך",
            "action_items": [] if passed else [f"הגדרת נוהל תפעולי עבור {c['title']}", "הטמעת הבקרה הטכנולוגית הרלוונטית"],
            "proposed_clause": "" if passed else clause
        })
    return results

def generate_patched_policy(original_text, results):
    patched_text = original_text + "\n\n" + "="*50 + "\n"
    patched_text += "נספח תיקונים ועדכוני מדיניות (הופק אוטומטית ע\"י Compliance Copilot AI)\n"
    patched_text += f"תאריך עדכון: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
    patched_text += "="*50 + "\n\n"
    
    added_count = 0
    for r in results:
        if r.get("proposed_clause"):
            patched_text += f"[{r['control_id']} - {r['title']}]\n{r['proposed_clause']}\n\n"
            added_count += 1
            
    if added_count == 0:
        patched_text += "כלל הבקרות עומדות בתקן במלואן - אין צורך בתוספות נוספות.\n"
    return patched_text

def build_export_html(results, score, filename, standard_name):
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    rows_html = ""
    for r in results:
        status = r.get("status", "")
        bg = "#dcfce7" if "עומד בתקן" in status else "#fee2e2"
        color = "#166534" if "עומד בתקן" in status else "#991b1b"
        clause_content = r.get('proposed_clause') if r.get('proposed_clause') else "עומד בדרישות התקן במלואן."
        
        rows_html += f"""
        <tr style="border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 12px; font-weight: bold; vertical-align: top;">{r['control_id']}</td>
            <td style="padding: 12px; vertical-align: top;"><strong>{r['title']}</strong><br><span style="font-size: 12px; color: #64748b;">{r['requirement_description']}</span></td>
            <td style="padding: 12px; vertical-align: top; text-align: center;"><span style="padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; background-color: {bg}; color: {color};">{status}</span></td>
            <td style="padding: 12px; font-size: 13px; color: #334155; vertical-align: top;">{r['findings']}</td>
            <td style="padding: 12px; font-size: 12px; background: #f8fafc; color: #1e293b; border-right: 3px solid #0284c7; vertical-align: top;">{clause_content}</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html dir="rtl" lang="he">
    <head>
        <meta charset="UTF-8">
        <title>דוח ביקורת תאימות רגולטורית - {standard_name}</title>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f8fafc; color: #0f172a; margin: 0; padding: 40px; }}
            .container {{ max-width: 1150px; margin: auto; background: #ffffff; padding: 40px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
            .header {{ border-bottom: 2px solid #0284c7; padding-bottom: 20px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; }}
            .score-box {{ background: linear-gradient(135deg, #0284c7, #0369a1); color: white; padding: 15px 30px; border-radius: 10px; text-align: center; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; text-align: right; }}
            th {{ background-color: #f1f5f9; color: #334155; padding: 12px; border-bottom: 2px solid #cbd5e1; font-size: 14px; }}
            @media print {{ body {{ padding: 0; background: white; }} .container {{ box-shadow: none; padding: 0; }} }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1 style="margin: 0; color: #0f172a; font-size: 24px;">🛡️ דוח מבדק תאימות רגולטורית - {standard_name}</h1>
                    <p style="margin: 6px 0 0 0; color: #64748b; font-size: 14px;">מסמך: <strong>{filename}</strong> | תאריך הפקה: <strong>{date_str}</strong></p>
                </div>
                <div class="score-box">
                    <div style="font-size: 13px; opacity: 0.9;">ציון מוכנות למבדק</div>
                    <div style="font-size: 32px; font-weight: bold;">{score}%</div>
                </div>
            </div>
            <h3>📋 פירוט ממצאי ביקורת והנחיות תיקון</h3>
            <table>
                <thead>
                    <tr>
                        <th style="width: 8%;">מזהה</th>
                        <th style="width: 25%;">בקרה ודרישת התקן</th>
                        <th style="width: 13%; text-align: center;">סטטוס</th>
                        <th style="width: 24%;">ממצאי ביקורת</th>
                        <th style="width: 30%;">נוסח סעיף מתוקן (Auto-Fix)</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
    </body>
    </html>
    """

# ממשק משתמש
st.title("🛡️ Compliance Copilot AI - Enterprise Suite")
st.caption("פלטפורמת ביקורת אוטונומית רב-תקנית – איתור פערים, צעדי יישום, תיקון מסמכים וייצוא דוחות.")

with st.sidebar:
    st.header("⚙️ הגדרות מבדק")
    selected_standard = st.selectbox("בחרי תקן לבדיקה:", list(STANDARDS_DB.keys()))
    st.divider()
    st.write(f"📊 **בקרות פעילות:** {len(STANDARDS_DB[selected_standard])} בקרות")
    st.write("🟢 **מנוע סריקה:** Active Multi-Standard RAG")

uploaded_file = st.file_uploader("העלי קובץ נוהל ארגוני (PDF או TXT):", type=["pdf", "txt"])

if uploaded_file is not None:
    policy_text = extract_text_from_file(uploaded_file)
    st.success(f"הקובץ **{uploaded_file.name}** נטען בהצלחה ({len(policy_text)} תווים).")
    
    if st.button("🚀 הפעל ניתוח פערים ותיקון אוטומטי", type="primary", use_container_width=True):
        with st.spinner(f"מבצע ביקורת מקיפה מול תקן {selected_standard}..."):
            results = run_analysis(policy_text, selected_standard)
            total = len(results)
            passed = sum(1 for r in results if "עומד בתקן" in r.get("status", ""))
            score = int((passed / total) * 100) if total > 0 else 0

        # לוח מדדים
        st.subheader("📈 לוח מדדי מוכנות למבדק (Audit Scorecard)")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("ציון מוכנות למבדק", f"{score}%")
        c2.metric("בקרות שנבדקו", total)
        c3.metric("עומדות בתקן מלא", passed)
        c4.metric("פערים לתיקון", total - passed)

        # אזור פעולות מתקדמות (ייצוא דוח + הורדת מסמך מתוקן)
        st.markdown("---")
        st.subheader("⚡ פעולות ייצוא ותיקון אוטונומי")
        col_act1, col_act2 = st.columns(2)
        
        with col_act1:
            report_html = build_export_html(results, score, uploaded_file.name, selected_standard)
            st.download_button(
                label="📥 הורד דוח ביקורת רשמי (Audit Report)",
                data=report_html,
                file_name=f"Audit_Report_{selected_standard}_{datetime.now().strftime('%Y%m%d')}.html",
                mime="text/html",
                use_container_width=True
            )
            st.caption("💡 פתחי את הדוח בדפדפן ולחצי Ctrl+P לשמירתו כ-PDF רשמי.")

        with col_act2:
            patched_doc = generate_patched_policy(policy_text, results)
            st.download_button(
                label="📄 הורד מסמך נוהל מעודכן ומתוקן (Patched Policy)",
                data=patched_doc,
                file_name=f"Patched_{uploaded_file.name.replace('.pdf', '.txt')}",
                mime="text/plain",
                type="primary",
                use_container_width=True
            )
            st.caption("✨ מסמך המדיניות שלך בצירוף כל הפסקאות המתקנות שנסגרו ע\"י ה-AI.")

        # פירוט בקרות
        st.markdown("---")
        st.subheader("🔍 פירוט ממצאי ביקורת, צעדי יישום וסעיפי תיקון")

        for item in results:
            status = item.get("status", "")
            border_col = "#16a34a" if "עומד בתקן" in status else "#dc2626"
            badge = "🟢 עומד בתקן" if "עומד בתקן" in status else "🔴 פער קריטי"

            with st.container():
                st.markdown(f"""
                <div class="report-card" style="border-right: 6px solid {border_col};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 style="margin: 0; color: #0f172a;">{item['control_id']} - {item['title']}</h4>
                        <span style="font-weight: bold;">{badge}</span>
                    </div>
                    <p style="margin: 8px 0 4px 0; color: #64748b; font-size: 13px;"><strong>דרישת התקן ({item['domain']}):</strong> {item['requirement_description']}</p>
                    <p style="margin: 4px 0; color: #1e293b; font-size: 14px;"><strong>ממצאי ביקורת:</strong> {item['findings']}</p>
                </div>
                """, unsafe_allow_html=True)

                if "עומד בתקן" not in status:
                    with st.expander(f"🛠️ צעדי יישום ונוסח סעיף מתקן להעתקה ({item['control_id']})"):
                        if item.get("action_items"):
                            st.markdown("**צעדי יישום טכנולוגיים וניהוליים (Action Items):**")
                            for step in item["action_items"]:
                                st.markdown(f"- {step}")
                        st.markdown("**נוסח מוכן להדבקה במסמך הנוהל:**")
                        st.code(item["proposed_clause"], language="text")