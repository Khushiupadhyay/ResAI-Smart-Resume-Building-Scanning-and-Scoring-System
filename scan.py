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
    return render_template('scan.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_job():
    data = request.json
    job_description = data.get('jobDescription', '')
    resume_data = data.get('resumeData', {})
    
    if not job_description:
        return jsonify({'error': 'Job description is required'}), 400
    
    try:
        # Get tailored recommendations based on the job description
        recommendations = get_job_recommendations(job_description, resume_data)
        return jsonify(recommendations)
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': 'Failed to analyze job description'}), 500

def get_job_recommendations(job_description, resume_data=None):
    """Use Gemini to analyze job description and provide tailored recommendations"""
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    # Extract key skills from job description
    skills_prompt = f"""
    Analyze this job description and extract the following:
    1. A list of 10-15 key hard skills that would be valuable for this role
    2. A list of 5-8 key soft skills that would be valuable for this role
    3. The 3-5 most important technical qualifications for this role
    
    Job Description:
    {job_description}
    
    Format your response as JSON with these keys: "hardSkills", "softSkills", "keyQualifications"
    Each should contain an array of strings.
    """
    
    skills_response = model.generate_content(skills_prompt)
    skills_text = skills_response.text.strip()
    
    # Clean up the response to ensure it's valid JSON
    skills_text = re.sub(r'```json', '', skills_text)
    skills_text = re.sub(r'```', '', skills_text)
    skills_data = json.loads(skills_text)
    
    # Get resume improvement suggestions
    improvement_prompt = f"""
    Based on this job description, provide specific recommendations for resume improvements:
    
    Job Description:
    {job_description}
    
    Provide the following:
    1. Three specific achievement examples that would impress for this role (with metrics)
    2. Five bullet points of ideal experience descriptions tailored to this role
    3. A tailored professional summary (3-4 sentences) for this role
    4. Three project ideas that would demonstrate relevant skills for this job
    
    Format your response as JSON with these keys: "achievements", "experienceBullets", "professionalSummary", "projectIdeas"
    Each (except professionalSummary which is a string) should contain an array of strings.
    """
    
    improvement_response = model.generate_content(improvement_prompt)
    improvement_text = improvement_response.text.strip()
    
    # Clean up the response to ensure it's valid JSON
    improvement_text = re.sub(r'```json', '', improvement_text)
    improvement_text = re.sub(r'```', '', improvement_text)
    improvement_data = json.loads(improvement_text)
    
    # Get ATS optimization tips
    ats_prompt = f"""
    Provide ATS (Applicant Tracking System) optimization tips for a resume targeting this job:
    
    Job Description:
    {job_description}
    
    Provide the following:
    1. Five keywords that should definitely appear in the resume
    2. Three formatting recommendations to improve ATS readability
    3. Three sections that should be prioritized for this particular job
    
    Format your response as JSON with these keys: "keywords", "formatting", "prioritySections"
    Each should contain an array of strings.
    """
    
    ats_response = model.generate_content(ats_prompt)
    ats_text = ats_response.text.strip()
    
    # Clean up the response to ensure it's valid JSON
    ats_text = re.sub(r'```json', '', ats_text)
    ats_text = re.sub(r'```', '', ats_text)
    ats_data = json.loads(ats_text)
    
    # Compile all recommendations
    recommendations = {
        "skills": {
            "hardSkills": skills_data.get("hardSkills", []),
            "softSkills": skills_data.get("softSkills", []),
            "keyQualifications": skills_data.get("keyQualifications", [])
        },
        "content": {
            "achievements": improvement_data.get("achievements", []),
            "experienceBullets": improvement_data.get("experienceBullets", []),
            "professionalSummary": improvement_data.get("professionalSummary", ""),
            "projectIdeas": improvement_data.get("projectIdeas", [])
        },
        "ats": {
            "keywords": ats_data.get("keywords", []),
            "formatting": ats_data.get("formatting", []),
            "prioritySections": ats_data.get("prioritySections", [])
        }
    }
    
    # If resume data was provided, add personalized gap analysis
    if resume_data:
        gap_analysis = get_gap_analysis(job_description, resume_data)
        recommendations["gapAnalysis"] = gap_analysis
    
    return recommendations

def get_gap_analysis(job_description, resume_data):
    """Analyze gaps between user's resume and job requirements"""
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    # Prepare resume summary for the model
    resume_summary = f"""
    Resume skills: {', '.join(resume_data.get('skills', []))}
    Experience: {json.dumps(resume_data.get('experience', []))}
    Education: {json.dumps(resume_data.get('education', []))}
    Projects: {json.dumps(resume_data.get('projects', []))}
    """
    
    gap_prompt = f"""
    Compare this resume information with the job description and identify gaps and improvement opportunities.
    
    Resume Information:
    {resume_summary}
    
    Job Description:
    {job_description}
    
    Provide the following:
    1. A list of missing skills that should be acquired or highlighted
    2. Experience gaps that might need to be addressed
    3. Specific recommendations to bridge these gaps
    
    Format your response as JSON with these keys: "missingSkills", "experienceGaps", "recommendations"
    Each should contain an array of strings.
    """
    
    gap_response = model.generate_content(gap_prompt)
    gap_text = gap_response.text.strip()
    
    # Clean up the response to ensure it's valid JSON
    gap_text = re.sub(r'```json', '', gap_text)
    gap_text = re.sub(r'```', '', gap_text)
    gap_data = json.loads(gap_text)
    
    return {
        "missingSkills": gap_data.get("missingSkills", []),
        "experienceGaps": gap_data.get("experienceGaps", []),
        "recommendations": gap_data.get("recommendations", [])
    }

@app.route('/api/enhance', methods=['POST'])
def enhance_resume_content():
    """Enhance specific resume sections based on job requirements"""
    data = request.json
    job_description = data.get('jobDescription', '')
    section_type = data.get('sectionType', '')  # e.g., 'summary', 'experience', 'project'
    section_content = data.get('content', '')
    
    if not job_description or not section_type or not section_content:
        return jsonify({'error': 'Missing required information'}), 400
    
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        enhance_prompt = f"""
        Enhance this resume {section_type} to better target the following job description:
        
        Current {section_type}:
        {section_content}
        
        Job Description:
        {job_description}
        
        Provide an enhanced version that:
        1. Incorporates relevant keywords from the job description
        2. Highlights achievements with metrics where possible
        3. Uses strong action verbs
        4. Is optimized for ATS systems
        5. Is concise and impactful
        
        Return only the enhanced content without explanations.
        """
        
        enhance_response = model.generate_content(enhance_prompt)
        enhanced_content = enhance_response.text.strip()
        
        return jsonify({
            'originalContent': section_content,
            'enhancedContent': enhanced_content
        })
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': 'Failed to enhance content'}), 500

@app.route('/api/keyword-density', methods=['POST'])
def analyze_keyword_density():
    """Analyze keyword usage in resume compared to job description"""
    data = request.json
    job_description = data.get('jobDescription', '')
    resume_text = data.get('resumeText', '')
    
    if not job_description or not resume_text:
        return jsonify({'error': 'Both job description and resume text are required'}), 400
    
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        prompt = f"""
        Analyze the keyword usage between this resume and job description.
        
        Job Description:
        {job_description}
        
        Resume Text:
        {resume_text}
        
        Provide the following analysis:
        1. Top 10 important keywords from the job description
        2. Keywords present in both the resume and job description
        3. Important keywords missing from the resume
        4. Recommendations for keyword optimization
        
        Format your response as JSON with these keys: "importantKeywords", "matchedKeywords", "missingKeywords", "recommendations"
        Each should contain an array of strings.
        """
        
        response = model.generate_content(prompt)
        analysis_text = response.text.strip()
        
        # Clean up the response to ensure it's valid JSON
        analysis_text = re.sub(r'```json', '', analysis_text)
        analysis_text = re.sub(r'```', '', analysis_text)
        analysis_data = json.loads(analysis_text)
        
        return jsonify(analysis_data)
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': 'Failed to analyze keyword density'}), 500

if __name__ == '__main__':
    app.run(debug=True)