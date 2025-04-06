from flask import Flask, request, jsonify, render_template, send_file
import json
import os
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
import uuid
import re
import google.generativeai as genai
from reportlab.pdfgen import canvas

app = Flask(__name__)

# Configure Gemini API - you'll need to get an API key from Google AI Studio
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyD5ZxapvHj822Q9JwGSBNJWkghliUaNtTE")
genai.configure(api_key=GEMINI_API_KEY)

# Store user conversations temporarily (in a real app, this would be a database)
conversations = {}

# Resume template types
# Resume template types with enhanced styling
TEMPLATES = {
    "professional": {
        "title_color": colors.navy,
        "section_color": colors.darkblue,
        "background_color": colors.white,
        "line_color": colors.gray,
        "font": "Helvetica",
        "line_spacing": 1.2,
        "paragraph_spacing": 8,
        "has_border": False
    },
    "creative": {
        "title_color": colors.darkgreen,
        "section_color": colors.green,
        "background_color": colors.white,
        "line_color": colors.lightgrey,
        "font": "Helvetica",
        "line_spacing": 1.2,
        "paragraph_spacing": 8,
        "has_border": False
    },
    "modern": {
        "title_color": colors.black,
        "section_color": colors.red,
        "background_color": colors.whitesmoke,
        "line_color": colors.darkgrey,
        "font": "Helvetica-Bold",
        "line_spacing": 1.5,
        "paragraph_spacing": 10,
        "has_border": False
    },
    "elegant": {
        "title_color": colors.darkslategray,
        "section_color": colors.darkslategray,
        "background_color": colors.ivory,
        "line_color": colors.gold,
        "font": "Times-Roman",
        "line_spacing": 1.3,
        "paragraph_spacing": 12,
        "has_border": True,
        "border_color": colors.gold,
        "border_width": 1
    },
    "vibrant": {
        "title_color": colors.purple,
        "section_color": colors.darkviolet,
        "background_color": colors.lavenderblush,
        "line_color": colors.mediumorchid,
        "font": "Helvetica-Bold",
        "line_spacing": 1.4,
        "paragraph_spacing": 10,
        "has_border": True,
        "border_color": colors.mediumorchid,
        "border_width": 0.5
    },
    "minimal": {
        "title_color": colors.black,
        "section_color": colors.black,
        "background_color": colors.white,
        "line_color": colors.black,
        "font": "Courier",
        "line_spacing": 1.1,
        "paragraph_spacing": 6,
        "has_border": False
    }
}

@app.route('/')
def index():
    return render_template('homepage.html')

@app.route('/resume_builder')
def resume_builder():
    return render_template('index.html')

@app.route('/scan')
def scan():
    return render_template('scan.html')

@app.route('/score')
def score():
    return render_template('score.html')
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    session_id = data.get('session_id', str(uuid.uuid4()))
    
    if session_id not in conversations:
        conversations[session_id] = {
            'state': 'greeting',
            'data': {
                'personal_info': {},
                'education': [],
                'experience': [],
                'certificates': [],
                'projects': [],
                'extra_curricular': [],
                'achievements': [],
                'skills': [],
                'template': 'professional',
                'summary': ''
            },
            'credits': 3  # Initialize with 3 credits for new users
        }
    
    conversation = conversations[session_id]
    response = process_message(user_message, conversation)
    
    return jsonify({
        'response': response,
        'session_id': session_id,
        'state': conversation['state'],
        'credits': conversation['credits']  # Return credits with the response
    })

@app.route('/api/generate-resume', methods=['POST'])
def generate_resume():
    data = request.json
    session_id = data.get('session_id')
    
    if session_id not in conversations:
        return jsonify({'error': 'Session not found'}), 404
    
    conversation = conversations[session_id]
    
    # Check if user has credits
    if conversation['credits'] <= 0:
        return jsonify({'error': 'No credits remaining'}), 403
    
    # Deduct a credit
    conversation['credits'] -= 1
    
    resume_data = conversation['data']
    template_type = resume_data.get('template', 'professional')
    
    # Generate enhanced content with Gemini API
    enhance_resume_content(resume_data)
    
    # Generate PDF
    buffer = BytesIO()
    create_pdf(resume_data, buffer, template_type)
    buffer.seek(0)
    
    # Reset conversation for a new resume
    remaining_credits = conversation['credits']
    conversation['data'] = {
        'personal_info': {},
        'education': [],
        'experience': [],
        'certificates': [],
        'projects': [],
        'extra_curricular': [],
        'achievements': [],
        'skills': [],
        'template': 'professional',
        'summary': ''
    }
    conversation['state'] = 'personal_info'
    
    # Return the PDF file
    response = send_file(
        buffer,
        as_attachment=True,
        download_name=f"resume_{session_id}.pdf",
        mimetype='application/pdf'
    )
    
    # Return the remaining credits count
    response.headers['X-Credits-Remaining'] = str(remaining_credits)
    response.headers['X-Next-State'] = 'personal_info'
    
    return response

@app.route('/api/get-credits', methods=['POST'])
def get_credits():
    data = request.json
    session_id = data.get('session_id')
    
    if session_id not in conversations:
        return jsonify({'error': 'Session not found'}), 404
    
    return jsonify({
        'credits': conversations[session_id]['credits']
    })

@app.route('/api/start-over', methods=['POST'])
def start_over():
    data = request.json
    session_id = data.get('session_id')
    
    if session_id not in conversations:
        return jsonify({'error': 'Session not found'}), 404
    
    # Reset conversation but preserve credits
    remaining_credits = conversations[session_id]['credits']
    
    # Create new conversation with the same session ID but preserving credits
    conversations[session_id] = {
        'state': 'greeting',
        'data': {
            'personal_info': {},
            'education': [],
            'experience': [],
            'certificates': [],
            'projects': [],
            'extra_curricular': [],
            'achievements': [],
            'skills': [],
            'template': 'professional',
            'summary': ''
        },
        'credits': remaining_credits
    }
    
    return jsonify({
        'response': f"Let's create a new resume! You have {remaining_credits} resume credits remaining. First, please tell me your full name.",
        'session_id': session_id,
        'state': 'personal_info',
        'credits': remaining_credits
    })

def process_message(message, conversation):
    state = conversation['state']
    data = conversation['data']
    
    # Handle the restart question state
    if state == 'ask_restart':
        if message.lower() in ['yes', 'y', 'start over', 'start again', 'create new', 'new resume']:
            # Check if credits remain before starting over
            if conversation['credits'] <= 0:
                return "Sorry, you have no resume credits remaining. Please contact support to purchase more credits."
            
            # Reset the conversation data but keep the credits
            conversation['data'] = {
                'personal_info': {},
                'education': [],
                'experience': [],
                'certificates': [],
                'projects': [],
                'extra_curricular': [],
                'achievements': [],
                'skills': [],
                'template': 'professional',
                'summary': ''
            }
            conversation['state'] = 'greeting'
            return f"Great! Let's create another resume. You have {conversation['credits']} resume credits remaining. First, please tell me your full name."
        else:
            # User doesn't want to start over
            conversation['state'] = 'complete'
            return f"No problem! Your resume has been generated. You still have {conversation['credits']} resume credits remaining if you change your mind."
    
    if state == 'greeting':
        conversation['state'] = 'personal_info'
        return f"Welcome to the Resume Builder Chatbot! You have {conversation['credits']} resume credits. Let's create your professional resume together. First, please tell me your full name."
    
    elif state == 'personal_info':
        if 'name' not in data['personal_info']:
            data['personal_info']['name'] = message
            return "Great! Now, please provide your email address."
        elif 'email' not in data['personal_info']:
            if re.match(r"[^@]+@[^@]+\.[^@]+", message):
                data['personal_info']['email'] = message
                return "Please provide your phone number."
            else:
                return "That doesn't look like a valid email address. Please try again."
        elif 'phone' not in data['personal_info']:
            data['personal_info']['phone'] = message
            return "Please provide your LinkedIn profile URL (or type 'skip' if you don't want to include it)."
        elif 'linkedin' not in data['personal_info']:
            if message.lower() != 'skip':
                data['personal_info']['linkedin'] = message
            return "Please provide a brief professional summary or objective statement (3-4 sentences about your career goals and experience)."
        elif 'summary' not in data['personal_info']:
            data['personal_info']['summary'] = message
            conversation['state'] = 'education'
            return "Now, let's add your education. Please provide your most recent degree, institution, and graduation year in this format: 'Degree, Institution, Year' (for example: 'Bachelor of Science in Computer Science, MIT, 2022')"
    
    elif state == 'education':
        if message.lower() == 'done':
            conversation['state'] = 'experience'
            return "Great! Now let's add your work experience. Please provide your job title, company, duration, and a brief description in this format: 'Job Title, Company, Duration, Description' (for example: 'Software Engineer, Google, 2018-2022, Developed and maintained web applications'). When you're finished adding experiences, type 'done'."
        
        parts = [part.strip() for part in message.split(',', 3)]
        if len(parts) >= 3:
            education_entry = {
                'degree': parts[0],
                'institution': parts[1],
                'year': parts[2],
                'enhanced_description': ''
            }
            data['education'].append(education_entry)
            return "Education added! Add another education entry or type 'done' to move on to work experience."
        else:
            return "Please provide your education information in the format: 'Degree, Institution, Year'"
    
    elif state == 'experience':
        if message.lower() == 'done':
            conversation['state'] = 'certificates'
            return "Now, let's add any professional certificates you have. For each certificate, please provide the name, issuing organization, and year in this format: 'Certificate Name, Issuing Organization, Year' (for example: 'AWS Certified Solutions Architect, Amazon Web Services, 2023'). If you don't have any certificates, type 'skip'."
        
        parts = [part.strip() for part in message.split(',', 3)]
        if len(parts) >= 3:
            experience_entry = {
                'title': parts[0],
                'company': parts[1],
                'duration': parts[2],
                'enhanced_description': ''
            }
            if len(parts) >= 4:
                experience_entry['description'] = parts[3]
            data['experience'].append(experience_entry)
            return "Experience added! Add another experience or type 'done' to move on to certificates."
        else:
            return "Please provide your experience in the format: 'Job Title, Company, Duration, Description'"
    
    elif state == 'certificates':
        if message.lower() == 'done' or message.lower() == 'skip':
            conversation['state'] = 'projects'
            return "Now, let's add any significant projects you've worked on. For each project, please provide the title, technologies used, and a brief description in this format: 'Project Title, Technologies, Description' (for example: 'E-commerce Platform, React/Node.js, Built a full-stack e-commerce platform with payment integration'). When you're finished adding projects, type 'done' or 'skip' if you don't have any to add."
        
        parts = [part.strip() for part in message.split(',', 2)]
        if len(parts) >= 3:
            certificate_entry = {
                'name': parts[0],
                'organization': parts[1],
                'year': parts[2],
                'enhanced_description': ''
            }
            data['certificates'].append(certificate_entry)
            return "Certificate added! Add another certificate or type 'done' to move on to projects."
        else:
            return "Please provide your certificate information in the format: 'Certificate Name, Issuing Organization, Year'"
    
    elif state == 'projects':
        if message.lower() == 'done' or message.lower() == 'skip':
            conversation['state'] = 'extra_curricular'
            return "Let's add your extra-curricular activities. Please provide each activity with a title, organization, and brief description in this format: 'Activity Title, Organization, Description' (for example: 'Volunteer Teacher, Community Center, Taught programming to underprivileged youth'). When you're finished, type 'done' or 'skip' if none to add."
        
        parts = [part.strip() for part in message.split(',', 2)]
        if len(parts) >= 3:
            project_entry = {
                'title': parts[0],
                'technologies': parts[1],
                'description': parts[2],
                'enhanced_description': ''
            }
            data['projects'].append(project_entry)
            return "Project added! Add another project or type 'done' to move on to extra-curricular activities."
        else:
            return "Please provide your project information in the format: 'Project Title, Technologies, Description'"
    
    elif state == 'extra_curricular':
        if message.lower() == 'done' or message.lower() == 'skip':
            conversation['state'] = 'achievements'
            return "Let's add your key achievements or awards. Please list each achievement with a title, organization, year, and brief description in this format: 'Achievement Title, Organization, Year, Description' (for example: 'Employee of the Year, ABC Corp, 2023, Recognized for exceptional performance and leadership'). When you're finished, type 'done' or 'skip' if none to add."
        
        parts = [part.strip() for part in message.split(',', 2)]
        if len(parts) >= 3:
            activity_entry = {
                'title': parts[0],
                'organization': parts[1],
                'description': parts[2],
                'enhanced_description': ''
            }
            data['extra_curricular'].append(activity_entry)
            return "Activity added! Add another activity or type 'done' to move on to achievements."
        else:
            return "Please provide your activity information in the format: 'Activity Title, Organization, Description'"
    
    elif state == 'achievements':
        if message.lower() == 'done' or message.lower() == 'skip':
            conversation['state'] = 'skills'
            return "Now, let's add your skills. Please list your skills separated by commas (for example: 'Python, JavaScript, Project Management, Communication')."
        
        parts = [part.strip() for part in message.split(',', 3)]
        if len(parts) >= 3:
            achievement_entry = {
                'title': parts[0],
                'organization': parts[1],
                'year': parts[2],
                'enhanced_description': ''
            }
            if len(parts) >= 4:
                achievement_entry['description'] = parts[3]
            data['achievements'].append(achievement_entry)
            return "Achievement added! Add another achievement or type 'done' to move on to skills."
        else:
            return "Please provide your achievement information in the format: 'Achievement Title, Organization, Year, Description'"
    
    elif state == 'skills':
        skills = [skill.strip() for skill in message.split(',')]
        data['skills'] = skills
        conversation['state'] = 'template'
        return "Great! Choose a resume template: 'professional' , 'creative' , 'modern' , 'elegant' , 'vibrant' , 'minimal'."
    
    elif state == 'template':
        if message.lower() in TEMPLATES.keys():
            data['template'] = message.lower()
            conversation['state'] = 'complete'
            return f"Your resume information is complete! You have {conversation['credits']} resume credits remaining. You can now generate your PDF resume by clicking the 'Generate Resume' button. We'll use AI to enhance your descriptions and create a polished resume!"
        else:
            available_templates = ', '.join(f"'{t}'" for t in TEMPLATES.keys())
            return f"Please choose one of the following templates: {available_templates}"
    
    elif state == 'complete':
        if message.lower() in ['restart', 'start over', 'new resume', 'start again', 'create new']:
            # Check if credits remain before starting over
            if conversation['credits'] <= 0:
                return "Sorry, you have no resume credits remaining. Please contact support to purchase more credits."
            
            # Reset the conversation data but keep the credits
            conversation['data'] = {
                'personal_info': {},
                'education': [],
                'experience': [],
                'certificates': [],
                'projects': [],
                'extra_curricular': [],
                'achievements': [],
                'skills': [],
                'template': 'professional',
                'summary': ''
            }
            conversation['state'] = 'personal_info'
            return f"Great! Let's create another resume. You have {conversation['credits']} resume credits remaining. First, please tell me your full name."
        else:
            return f"Your resume information is already complete. You have {conversation['credits']} resume credits remaining. You can generate your PDF resume by clicking the 'Generate Resume' button, or type 'start over' to create a new resume."
    
    return "I didn't understand that. Please try again."

def enhance_resume_content(resume_data):
    """Use Gemini to enhance resume content with professional paragraphs"""
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    try:
        # Enhance professional summary
        if 'summary' in resume_data['personal_info']:
            prompt = f"""
            Create a professional resume summary paragraph based on this information:
            Summary: {resume_data['personal_info']['summary']}
            Work experience: {', '.join([f"{exp['title']} at {exp['company']}" for exp in resume_data['experience']])}
            Skills: {', '.join(resume_data['skills'])}
            
            Write in first person, be concise, professional, and highlight key strengths. 
            Maximum 4 sentences. No greeting or explanation, just the paragraph.
            """
            
            response = model.generate_content(prompt)
            resume_data['summary'] = response.text.strip()
        
        # Enhance experience descriptions
        for exp in resume_data['experience']:
            if 'description' in exp:
                prompt = f"""
                Transform this job description into 3-4 professional bullet points for a resume:
                Job Title: {exp['title']}
                Company: {exp['company']}
                Duration: {exp['duration']}
                Description: {exp['description']}
                
                Each bullet should start with a strong action verb and include specific achievements 
                or responsibilities. Focus on impact and quantifiable results where possible.
                Return only the bullet points, separated by newlines, without any explanation.
                """
                
                response = model.generate_content(prompt)
                exp['enhanced_description'] = response.text.strip()
        
        # Enhance certificate descriptions
        for cert in resume_data['certificates']:
            prompt = f"""
            Create a concise and impactful description for this professional certificate on a resume:
            Certificate: {cert['name']}
            Organization: {cert['organization']}
            Year: {cert['year']}
            
            Focus on the relevance to career goals, skills validated, and industry recognition.
            Write as a single brief sentence. No explanation, just the description.
            """
            
            response = model.generate_content(prompt)
            cert['enhanced_description'] = response.text.strip()
        
        # Enhance project descriptions
        for project in resume_data['projects']:
            if 'description' in project:
                prompt = f"""
                Transform this project description into 2-3 impactful bullet points for a resume:
                Project: {project['title']}
                Technologies: {project['technologies']}
                Description: {project['description']}
                
                Focus on your role, technical challenges overcome, and measurable outcomes.
                Each bullet should start with a strong action verb.
                Return only the bullet points, separated by newlines, without any explanation.
                """
                
                response = model.generate_content(prompt)
                project['enhanced_description'] = response.text.strip()
        
        # Enhance extra-curricular descriptions
        for activity in resume_data['extra_curricular']:
            if 'description' in activity:
                prompt = f"""
                Create a concise and impactful description for this extra-curricular activity on a resume:
                Activity: {activity['title']}
                Organization: {activity['organization']}
                Description: {activity['description']}
                
                Focus on transferable skills, leadership, and personal growth.
                Write as a single impactful sentence. No explanation, just the description.
                """
                
                response = model.generate_content(prompt)
                activity['enhanced_description'] = response.text.strip()
        
        # Enhance achievements
        for achievement in resume_data['achievements']:
            description = achievement.get('description', '')
            prompt = f"""
            Create an impactful statement for this achievement on a resume:
            Achievement: {achievement['title']}
            Organization: {achievement['organization']}
            Year: {achievement['year']}
            Description: {description}
            
            Focus on quantifiable results and impact. Use strong action verbs.
            Write as a single concise statement. No explanation, just the statement.
            """
            
            response = model.generate_content(prompt)
            achievement['enhanced_description'] = response.text.strip()
        
        # Enhance skills section
        if resume_data['skills']:
            prompt = f"""
            Organize these skills into categories for a resume:
            {', '.join(resume_data['skills'])}
            
            Format the result as a paragraph that groups similar skills together.
            Be concise and professional. No explanation, just the paragraph.
            """
            
            response = model.generate_content(prompt)
            resume_data['enhanced_skills'] = response.text.strip()
    
    except Exception as e:
        print(f"Error in Gemini API call: {e}")
        # Fall back to original content if API fails
    
    return resume_data

def create_pdf(data, buffer, template_type='professional'):
    # Get template colors and styles
    template = TEMPLATES.get(template_type, TEMPLATES['professional'])
    
    # Set up the document with background color
    from reportlab.lib.pagesizes import letter
    width, height = letter
    
    # Create a custom PageTemplate with background
    from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
    
    class BackgroundCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            self.template = template
            canvas.Canvas.__init__(self, *args, **kwargs)
        
        def showPage(self):
            # Draw background color
            self.setFillColor(self.template.get('background_color', colors.white))
            self.rect(0, 0, width, height, fill=1, stroke=0)
            
            # Draw border if specified
            if self.template.get('has_border', False):
                self.setStrokeColor(self.template.get('border_color', colors.black))
                self.setLineWidth(self.template.get('border_width', 1))
                margin = 20  # Border margin
                self.rect(margin, margin, width - 2*margin, height - 2*margin, fill=0, stroke=1)
            
            canvas.Canvas.showPage(self)
    
    doc = BaseDocTemplate(buffer, pagesize=letter)
    frame = Frame(30, 30, width - 60, height - 60, id='normal')
    template_page = PageTemplate(id='background', frames=frame, onPage=lambda c, d: None)
    doc.addPageTemplates([template_page])
    
    # Replace the Canvas class with our BackgroundCanvas
    doc.canv = BackgroundCanvas(buffer, pagesize=letter)
    
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Use the template's font
    font_name = template.get('font', 'Helvetica')
    line_spacing = template.get('line_spacing', 1.2)
    paragraph_spacing = template.get('paragraph_spacing', 8)
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=16,
        alignment=TA_CENTER,
        textColor=template['title_color'],
        spaceAfter=paragraph_spacing * 2,
        leading=16 * line_spacing
    )
    
    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=12,
        textColor=template['section_color'],
        spaceAfter=paragraph_spacing,
        spaceBefore=paragraph_spacing * 1.5,
        leading=12 * line_spacing
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontName=font_name,
        textColor=colors.black,
        spaceBefore=paragraph_spacing / 2,
        spaceAfter=paragraph_spacing / 2,
        leading=10 * line_spacing
    )
    
    bullet_style = ParagraphStyle(
        'Bullet',
        parent=normal_style,
        leftIndent=20,
        firstLineIndent=-15,
        spaceBefore=paragraph_spacing / 3,
        spaceAfter=paragraph_spacing / 3
    )
    
    # Personal Information
    personal_info = data.get('personal_info', {})
    elements.append(Paragraph(personal_info.get('name', 'Name Not Provided'), title_style))
    
    contact_info = []
    if 'email' in personal_info:
        contact_info.append(personal_info['email'])
    if 'phone' in personal_info:
        contact_info.append(personal_info['phone'])
    if 'linkedin' in personal_info:
        contact_info.append(personal_info['linkedin'])
    
    elements.append(Paragraph(' | '.join(contact_info), ParagraphStyle(
        'Contact',
        parent=normal_style,
        alignment=TA_CENTER
    )))
    elements.append(Spacer(1, 12))
    
    # Professional Summary Section
    if 'summary' in data:
        elements.append(Paragraph('PROFESSIONAL SUMMARY', section_style))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(data['summary'], ParagraphStyle(
            'Summary',
            parent=normal_style,
            alignment=TA_JUSTIFY
        )))
        elements.append(Spacer(1, 12))
    
    # Education Section
    if data.get('education'):
        elements.append(Paragraph('EDUCATION', section_style))
        elements.append(Spacer(1, 6))
        
        for edu in data['education']:
            degree_text = f"<b>{edu.get('degree', '')}</b>, {edu.get('institution', '')}, {edu.get('year', '')}"
            elements.append(Paragraph(degree_text, normal_style))
            if 'enhanced_description' in edu and edu['enhanced_description']:
                elements.append(Paragraph(edu['enhanced_description'], ParagraphStyle(
                    'Description',
                    parent=normal_style,
                    leftIndent=20
                )))
            elements.append(Spacer(1, 6))
        
        elements.append(Spacer(1, 12))
    
    # Experience Section
    if data.get('experience'):
        elements.append(Paragraph('PROFESSIONAL EXPERIENCE', section_style))
        elements.append(Spacer(1, 6))
        
        for exp in data['experience']:
            job_text = f"<b>{exp.get('title', '')}</b>, {exp.get('company', '')}, {exp.get('duration', '')}"
            elements.append(Paragraph(job_text, normal_style))
            
            # Use enhanced description if available, otherwise fall back to original
            if 'enhanced_description' in exp and exp['enhanced_description']:
                # Split the bullet points
                bullets = exp['enhanced_description'].split('\n')
                for bullet in bullets:
                    if bullet.strip():
                        if not bullet.startswith('•'):
                            bullet = '• ' + bullet
                        elements.append(Paragraph(bullet, bullet_style))
            elif 'description' in exp:
                elements.append(Paragraph(exp['description'], ParagraphStyle(
                    'Description',
                    parent=normal_style,
                    leftIndent=20
                )))
            
            elements.append(Spacer(1, 8))
        
        elements.append(Spacer(1, 12))
    
    # Projects Section
    if data.get('projects'):
        elements.append(Paragraph('PROJECTS', section_style))
        elements.append(Spacer(1, 6))
        
        for project in data['projects']:
            project_text = f"<b>{project.get('title', '')}</b> - {project.get('technologies', '')}"
            elements.append(Paragraph(project_text, normal_style))
            
            # Use enhanced description if available, otherwise fall back to original
            if 'enhanced_description' in project and project['enhanced_description']:
                bullets = project['enhanced_description'].split('\n')
                for bullet in bullets:
                    if bullet.strip():
                        if not bullet.startswith('•'):
                            bullet = '• ' + bullet
                        elements.append(Paragraph(bullet, bullet_style))
            elif 'description' in project:
                elements.append(Paragraph(project['description'], ParagraphStyle(
                    'Description',
                    parent=normal_style,
                    leftIndent=20
                )))
            
            elements.append(Spacer(1, 6))
        
        elements.append(Spacer(1, 12))
    
    # Projects Section
    if data.get('projects'):
        elements.append(Paragraph('PROJECTS', section_style))
        elements.append(Spacer(1, 6))
        
        for project in data['projects']:
            project_text = f"<b>{project.get('title', '')}</b> - {project.get('technologies', '')}"
            elements.append(Paragraph(project_text, normal_style))
            
            # Use enhanced description if available, otherwise fall back to original
            if 'enhanced_description' in project and project['enhanced_description']:
                bullets = project['enhanced_description'].split('\n')
                for bullet in bullets:
                    if bullet.strip():
                        if not bullet.startswith('•'):
                            bullet = '• ' + bullet
                        elements.append(Paragraph(bullet, bullet_style))
            elif 'description' in project:
                elements.append(Paragraph(project['description'], ParagraphStyle(
                    'Description',
                    parent=normal_style,
                    leftIndent=20
                )))
            
            elements.append(Spacer(1, 6))
        
        elements.append(Spacer(1, 12))
    
    # Certificates Section
    if data.get('certificates'):
        elements.append(Paragraph('CERTIFICATIONS', section_style))
        elements.append(Spacer(1, 6))
        
        for cert in data['certificates']:
            cert_text = f"<b>{cert.get('name', '')}</b>, {cert.get('organization', '')}, {cert.get('year', '')}"
            elements.append(Paragraph(cert_text, normal_style))
            if 'enhanced_description' in cert and cert['enhanced_description']:
                elements.append(Paragraph(cert['enhanced_description'], ParagraphStyle(
                    'Description',
                    parent=normal_style,
                    leftIndent=20
                )))
            elements.append(Spacer(1, 6))
        
        elements.append(Spacer(1, 12))
    
    # Achievements Section
    if data.get('achievements'):
        elements.append(Paragraph('ACHIEVEMENTS & AWARDS', section_style))
        elements.append(Spacer(1, 6))
        
        for achievement in data['achievements']:
            achievement_text = f"<b>{achievement.get('title', '')}</b>, {achievement.get('organization', '')}, {achievement.get('year', '')}"
            elements.append(Paragraph(achievement_text, normal_style))
            if 'enhanced_description' in achievement and achievement['enhanced_description']:
                elements.append(Paragraph(achievement['enhanced_description'], ParagraphStyle(
                    'Description',
                    parent=normal_style,
                    leftIndent=20
                )))
            elements.append(Spacer(1, 6))
        
        elements.append(Spacer(1, 12))
    
    # Extra-Curricular Activities Section
    if data.get('extra_curricular'):
        elements.append(Paragraph('EXTRA-CURRICULAR ACTIVITIES', section_style))
        elements.append(Spacer(1, 6))
        
        for activity in data['extra_curricular']:
            activity_text = f"<b>{activity.get('title', '')}</b>, {activity.get('organization', '')}"
            elements.append(Paragraph(activity_text, normal_style))
            if 'enhanced_description' in activity and activity['enhanced_description']:
                elements.append(Paragraph(activity['enhanced_description'], ParagraphStyle(
                    'Description',
                    parent=normal_style,
                    leftIndent=20
                )))
            elements.append(Spacer(1, 6))
        
        elements.append(Spacer(1, 12))
    
    # Skills Section
    elements.append(Paragraph('SKILLS', section_style))
    elements.append(Spacer(1, 6))
    
    # Use enhanced skills if available, otherwise fall back to original list
    if 'enhanced_skills' in data and data['enhanced_skills']:
        elements.append(Paragraph(data['enhanced_skills'], ParagraphStyle(
            'SkillsText',
            parent=normal_style,
            alignment=TA_JUSTIFY
        )))
    else:
        skills_text = ', '.join(data.get('skills', []))
        elements.append(Paragraph(skills_text, normal_style))
    
    # Build the PDF
    doc.build(elements)

#ANALYSE SECTION
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
def enhance_resume_section():
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
    app.run(debug=True)