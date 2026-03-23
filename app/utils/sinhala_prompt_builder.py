# app/utils/sinhala_prompt_builder.py
 
from typing import Optional
 
def build_qa_prompt(context: str, count: int, query: Optional[str] = None) -> str:
    query_part = f"ඉල්ලීම: {query}\n\n" if query else ""
 
    return f"""
ඔබට පහත **තෝරාගත් පාඩම් අන්තර්ගත කොටස්** ලබා දී ඇත.
මෙම අන්තර්ගතය මත පදනම්ව සිංහල ප්‍රශ්න {count}ක් සහ පිළිතුරු {count}ක් සාදන්න.
 
{query_part}🔒 **නියම:**
1. **තෝරාගත් අන්තර්ගතයේ පමණක්** ඇති කරුණු පමණක් භාවිතා කරන්න.
2. නව කරුණු, වෙළඳ නාම, නගර, සිදුවීම් හඳුන්වා නොදෙන්න.
3. සෑම ප්‍රශ්නයක්ම ලබා දී ඇති අන්තර්ගතයට සෘජුව සම්බන්ධ විය යුතුය.
4. **තෝරාගත් කොටස් වල නොමැති කරුණු ගැන ප්‍රශන නොකරන්න**.
 
📚 **තෝරාගත් අන්තර්ගත කොටස්:**
{context}
 
**ආකෘතිය:**
1. ප්‍රශ්නය: ...
   පිළිතුර: ...
(මෙලෙස {count}ක්)
"""
 
def build_direct_answer_prompt(
    context: str, 
    query: str, 
    grade: Optional[str] = None
) -> str:
    """
    Build prompt for direct Q&A with optional grade adaptation
    """
    
    # Mapping specific complexity instructions based on grade level
    grade_instructions = {
        "6-8": "පිළිතුර ඉතාමත් සරල සිංහල භාෂාවෙන් සහ කෙටි වාක්‍යවලින් (වචන 10-15) සකසන්න.",
        "9-11": "පිළිතුර සම්මත සිංහල භාෂාවෙන් සහ පැහැදිලි මධ්‍යම ප්‍රමාණයේ වාක්‍යවලින් සකසන්න.",
        "12-13": "පිළිතුර විද්‍යාත්මක/ශාස්ත්‍රීය සිංහල භාෂාවෙන් සහ ගැඹුරු විග්‍රහ සහිතව සකසන්න.",
        "university": "පිළිතුර උසස් අධ්‍යයන සිංහල භාෂාවෙන්, විච්ඡේදනාත්මක සහ සවිස්තරාත්මකව සකසන්න."
    }

    # Get the specific instruction if grade is provided, otherwise empty
    level_instruction = ""
    if grade in grade_instructions:
        level_instruction = f"\n5. {grade_instructions[grade]}"
    elif grade:
        level_instruction = f"\n5. පිළිතුර {grade} මට්ටමට ගැළපෙන පරිදි සකස් කරන්න."

    return f"""
ඔබට පහත **තෝරාගත් අන්තර්ගත කොටස්** ලබා දී ඇත. 

🔴 **කාර්යය:**
පහත ප්‍රශ්නයට **සෘජු පිළිතුරක් පමණක්** ලබා දෙන්න.

❗ **වැදගත් නියම (ZERO HALLUCINATION):**
1. ලබා දී ඇති අන්තර්ගතයේ **පවතින කරුණු පමණක්** භාවිතා කරන්න.
2. අන්තර්ගතයේ නොමැති සංකල්ප, යුග, සිදුවීම් හෝ අලුත් උදාහරණ එකතු නොකරන්න.
3. ප්‍රශ්නයට සෘජුවම අදාළ නොවන හැඳින්වීම් (උදා: "ඉතිහාසය යනු...") ඇතුළත් නොකරන්න.
4. පිළිතුර සෘජුවම ප්‍රශ්නයට අදාළ කරුණු මත පදනම් විය යුතුය.{level_instruction}

🟡 **ප්‍රශ්නය:**
{query}

📚 **අන්තර්ගතය:**
{context}

✍️ **සෘජු පිළිතුර:**
"""
