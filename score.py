from flask import Flask, request, jsonify, render_template
import os
import re
import google.generativeai as genai
import json

app = Flask(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyD5ZxapvHj822Q9JwGSBNJWkghliUaNtTE")
genai.configure(api_key=GEMINI_API_KEY)

@app.route('/')
def index():
    return render_template('score.html')

@app.route('/api/quality-check', methods=['POST'])
def check_resume_quality():
    """Check resume for grammar, formatting issues and provide a quality score"""
    data = request.json
    resume_text = data.get('resumeText', '')
    job_description = data.get('jobDescription', '')  # Optional, enhances scoring relevance
    
    if not resume_text:
        return jsonify({'error': 'Resume text is required'}), 400
    
    try:
        # Get grammar and formatting checks
        grammar_check = check_grammar_formatting(resume_text)
        
        # Get resume score
        score_analysis = score_resume(resume_text, job_description)
        
        # Combine results
        results = {
            "grammarCheck": grammar_check,
            "scoreAnalysis": score_analysis
        }
        
        return jsonify(results)
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': 'Failed to analyze resume quality'}), 500

def check_grammar_formatting(resume_text):
    """Use Gemini to check grammar, spelling, and formatting issues"""
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    grammar_prompt = f"""
    Perform a detailed grammar and formatting check on this resume text. 
    Identify and categorize issues in these areas:
    
    Resume Text:
    {resume_text}
    
    Provide the following analysis:
    1. Spelling errors (word and correction)
    2. Grammar issues (problem and suggestion)
    3. Sentences over 25 words that should be shortened
    4. Formatting inconsistencies (bullet styles, spacing, etc.)
    5. Punctuation errors
    
    Format your response as JSON with these keys:
    - "spellingErrors": Array of objects with "word" and "correction"
    - "grammarIssues": Array of objects with "issue" and "suggestion"
    - "longSentences": Array of strings containing sentences that are too long
    - "formattingIssues": Array of strings describing formatting problems
    - "punctuationErrors": Array of objects with "error" and "correction"
    - "overallAssessment": A string with 1-2 sentences summarizing the quality
    """
    
    grammar_response = model.generate_content(grammar_prompt)
    grammar_text = grammar_response.text.strip()
    
    # Clean up the response to ensure it's valid JSON
    grammar_text = re.sub(r'```json', '', grammar_text)
    grammar_text = re.sub(r'```', '', grammar_text)
    grammar_data = json.loads(grammar_text)
    
    return grammar_data

def score_resume(resume_text, job_description=None):
    """Score resume quality and provide improvement recommendations"""
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    # Add job context if available
    job_context = ""
    if job_description:
        job_context = f"""
        Job Description Context:
        {job_description}
        
        When scoring, consider how well the resume aligns with the above job description.
        """
    
    score_prompt = f"""
    Evaluate this resume and provide a detailed scoring analysis:
    
    Resume Text:
    {resume_text}
    
    {job_context}
    
    Score the resume in these categories on a scale of 1-10:
    
    1. Content Quality: Evaluate the strength of achievements, details, and clarity
    2. Keyword Optimization: Assess use of industry-relevant keywords and terminology
    3. Formatting & Structure: Evaluate organization, layout consistency, and readability
    4. Impact & Achievement Focus: Rate how well achievements are quantified with metrics
    5. Professional Language: Assess use of action verbs and professional vocabulary
    6. Completeness: Evaluate if all essential sections are included with adequate detail
    
    For each category:
    - Provide the numerical score (1-10)
    - Give 2-3 specific strengths
    - Give 2-3 specific improvement recommendations
    
    Also calculate an overall score (weighted average of all categories).
    
    Format your response as JSON with these keys:
    - "overallScore": A number from 1-100
    - "categoryScores": An object with keys for each category and values from 1-10
    - "strengths": An object with keys for each category and values as arrays of strings
    - "improvements": An object with keys for each category and values as arrays of strings
    - "priorityRecommendations": Array of 3 most important improvement actions
    """
    
    score_response = model.generate_content(score_prompt)
    score_text = score_response.text.strip()
    
    # Clean up the response to ensure it's valid JSON
    score_text = re.sub(r'```json', '', score_text)
    score_text = re.sub(r'```', '', score_text)
    score_data = json.loads(score_text)
    
    return score_data

@app.route('/api/advanced-formatting', methods=['POST'])
def check_advanced_formatting():
    """Analyze advanced formatting aspects of the resume"""
    data = request.json
    resume_text = data.get('resumeText', '')
    
    if not resume_text:
        return jsonify({'error': 'Resume text is required'}), 400
    
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        format_prompt = f"""
        Analyze the formatting and structure of this resume:
        
        Resume Text:
        {resume_text}
        
        Provide the following analysis:
        1. Consistency of date formats (are they all in the same format?)
        2. Consistent use of bullet points or paragraphs in similar sections
        3. White space balance (too crowded or too sparse?)
        4. Section heading consistency
        5. Font or emphasis consistency (based on capitalization patterns)
        6. Use of action verbs at the beginning of bullet points
        7. Formatting recommendations specific to ATS systems
        
        Format your response as JSON with these keys:
        - "dateFormatting": Object with "consistent" (boolean) and "issues" (array of strings)
        - "bulletConsistency": Object with "consistent" (boolean) and "issues" (array of strings)
        - "whiteSpace": Object with "assessment" (string) and "recommendations" (array of strings)
        - "headingConsistency": Object with "consistent" (boolean) and "issues" (array of strings)
        - "emphasisConsistency": Object with "assessment" (string) and "issues" (array of strings)
        - "actionVerbUsage": Object with "percentage" (number) and "improvements" (array of strings)
        - "atsFormatting": Array of strings with ATS-specific recommendations
        - "overallFormattingScore": Number from 1-10
        """
        
        format_response = model.generate_content(format_prompt)
        format_text = format_response.text.strip()
        
        # Clean up the response to ensure it's valid JSON
        format_text = re.sub(r'```json', '', format_text)
        format_text = re.sub(r'```', '', format_text)
        format_data = json.loads(format_text)
        
        return jsonify(format_data)
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': 'Failed to analyze resume formatting'}), 500

@app.route('/api/comprehensive-score', methods=['POST'])
def comprehensive_resume_score():
    """Generate a comprehensive resume score with detailed feedback"""
    data = request.json
    resume_text = data.get('resumeText', '')
    job_description = data.get('jobDescription', '')
    
    if not resume_text:
        return jsonify({'error': 'Resume text is required'}), 400
    
    try:
        # Get grammar and basic formatting checks
        grammar_check = check_grammar_formatting(resume_text)
        
        # Get content score and recommendations
        score_analysis = score_resume(resume_text, job_description)
        
        # Get advanced formatting analysis if job description is provided
        if job_description:
            # Analyze keyword relevance to job description
            keyword_data = analyze_keyword_relevance(resume_text, job_description)
        else:
            keyword_data = {"relevanceScore": 0, "message": "No job description provided for keyword analysis"}
        
        # Calculate final comprehensive score
        # 30% grammar, 40% content quality, 30% keyword relevance (if job provided)
        grammar_score = 10 - (len(grammar_check.get("spellingErrors", [])) + 
                             len(grammar_check.get("grammarIssues", [])) + 
                             len(grammar_check.get("punctuationErrors", []))) / 5
        
        # Ensure grammar score is between 1-10
        grammar_score = max(1, min(10, grammar_score))
        
        content_score = score_analysis.get("overallScore", 0) / 10  # Convert 1-100 to 1-10
        
        if job_description:
            keyword_score = keyword_data.get("relevanceScore", 0)
            final_score = (grammar_score * 0.3) + (content_score * 0.4) + (keyword_score * 0.3)
        else:
            final_score = (grammar_score * 0.5) + (content_score * 0.5)
        
        # Scale to 0-100
        final_score = round(final_score * 10)
        
        results = {
            "finalScore": final_score,
            "grammarScore": round(grammar_score * 10),
            "contentScore": score_analysis.get("overallScore", 0),
            "keywordScore": keyword_data.get("relevanceScore", 0) * 10 if job_description else None,
            "grammarCheck": grammar_check,
            "contentAnalysis": score_analysis,
            "keywordAnalysis": keyword_data if job_description else None,
            "priorityImprovements": generate_priority_improvements(grammar_check, score_analysis, keyword_data if job_description else None)
        }
        
        return jsonify(results)
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': 'Failed to generate comprehensive score'}), 500

def analyze_keyword_relevance(resume_text, job_description):
    """Analyze how well the resume keywords match the job description"""
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    keyword_prompt = f"""
    Analyze how well the resume's keywords and terminology match this job description:
    
    Job Description:
    {job_description}
    
    Resume Text:
    {resume_text}
    
    Provide the following analysis:
    1. A relevance score from 1-10 indicating how well the resume's keywords match the job
    2. Top 10 relevant keywords from the job description
    3. Keywords successfully included in the resume
    4. Important keywords missing from the resume
    5. Industry-specific terminology present in the job but missing in the resume
    
    Format your response as JSON with these keys:
    - "relevanceScore": Number from 1-10
    - "keyJobKeywords": Array of strings
    - "matchedKeywords": Array of strings
    - "missingKeywords": Array of strings
    - "missingTerminology": Array of strings
    - "recommendedAdditions": Array of strings (suggestions of what to add)
    """
    
    keyword_response = model.generate_content(keyword_prompt)
    keyword_text = keyword_response.text.strip()
    
    # Clean up the response to ensure it's valid JSON
    keyword_text = re.sub(r'```json', '', keyword_text)
    keyword_text = re.sub(r'```', '', keyword_text)
    keyword_data = json.loads(keyword_text)
    
    return keyword_data

def generate_priority_improvements(grammar_check, score_analysis, keyword_analysis=None):
    """Generate a prioritized list of improvements from all analyses"""
    priorities = []
    
    # Add grammar priorities (up to 2)
    grammar_issues = []
    if len(grammar_check.get("spellingErrors", [])) > 3:
        grammar_issues.append(f"Correct {len(grammar_check.get('spellingErrors', []))} spelling errors")
    if len(grammar_check.get("grammarIssues", [])) > 2:
        grammar_issues.append(f"Fix {len(grammar_check.get('grammarIssues', []))} grammar issues")
    if len(grammar_check.get("longSentences", [])) > 2:
        grammar_issues.append(f"Shorten {len(grammar_check.get('longSentences', []))} overly long sentences")
    
    # Take 2 most important grammar issues
    priorities.extend(grammar_issues[:2])
    
    # Add 2 content improvement priorities
    if "priorityRecommendations" in score_analysis:
        priorities.extend(score_analysis.get("priorityRecommendations", [])[:2])
    
    # Add 1 keyword improvement if available
    if keyword_analysis and "recommendedAdditions" in keyword_analysis and keyword_analysis.get("recommendedAdditions", []):
        priorities.append(f"Add these keywords: {', '.join(keyword_analysis.get('recommendedAdditions', [])[:3])}")
    
    # Ensure we have at most 5 priorities
    return priorities[:5]

@app.route('/api/fix-resume', methods=['POST'])
def fix_resume_issues():
    """Generate an improved version of the resume that fixes identified issues"""
    data = request.json
    resume_text = data.get('resumeText', '')
    job_description = data.get('jobDescription', '')
    issues_to_fix = data.get('issues', [])  # List of issue types to focus on
    
    if not resume_text:
        return jsonify({'error': 'Resume text is required'}), 400
    
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Build a customized prompt based on the issues to fix
        focus_areas = ""
        if issues_to_fix:
            focus_areas = "Focus especially on fixing these issues:\n"
            for issue in issues_to_fix:
                focus_areas += f"- {issue}\n"
        
        job_context = ""
        if job_description:
            job_context = f"""
            Consider this job description when improving the resume:
            {job_description}
            """
        
        fix_prompt = f"""
        Improve this resume by fixing grammar, formatting, and content issues:
        
        Original Resume:
        {resume_text}
        
        {job_context}
        
        {focus_areas}
        
        Provide the following:
        1. An improved version of the resume with all issues fixed
        2. A summary of the changes made
        
        Format your response as JSON with these keys:
        - "improvedResume": String containing the complete improved resume
        - "changesSummary": Array of strings describing the key changes made
        """
        
        fix_response = model.generate_content(fix_prompt)
        fix_text = fix_response.text.strip()
        
        # Clean up the response to ensure it's valid JSON
        fix_text = re.sub(r'```json', '', fix_text)
        fix_text = re.sub(r'```', '', fix_text)
        fix_data = json.loads(fix_text)
        
        return jsonify(fix_data)
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': 'Failed to generate improved resume'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)