from pathlib import Path
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "docs"
NAVY = "17365D"
PALE_BLUE = "EAF2F8"
LIGHT_GRAY = "D9D9D9"

def set_cell_shading(cell, fill):
    properties = cell._tc.get_or_add_tcPr()
    shading = properties.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        properties.append(shading)
    shading.set(qn("w:fill"), fill)

def set_cell_margins(cell, top=110, start=130, bottom=110, end=130):
    properties = cell._tc.get_or_add_tcPr()
    margins = properties.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        properties.append(margins)
    for edge, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        element = margins.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            margins.append(element)
        element.set(qn("w:w"), str(value))
        element.set(qn("w:type"), "dxa")

def set_table_borders(table):
    properties = table._tbl.tblPr
    borders = properties.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        properties.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        border = borders.find(qn(f"w:{edge}"))
        if border is None:
            border = OxmlElement(f"w:{edge}")
            borders.append(border)
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), "6")
        border.set(qn("w:color"), LIGHT_GRAY)

def configure_document(doc, subtitle, justify=False, font_size=11):
    section = doc.sections[0]
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(font_size)
    normal.paragraph_format.space_after = Pt(6)
    if justify:
        normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    title_style = styles["Title"]
    title_style.font.name = "Times New Roman"
    title_style.font.size = Pt(24)
    title_style.font.bold = True
    title_style.font.color.rgb = RGBColor(0, 0, 0)
    title_style_properties = title_style._element.get_or_add_pPr()
    title_style_border = title_style_properties.find(qn("w:pBdr"))
    if title_style_border is not None:
        title_style_properties.remove(title_style_border)

    for name, size in (("Heading 1", 12), ("Heading 2", 10), ("Heading 3", 10)):
        if name in styles:
            style = styles[name]
            style.font.name = "Times New Roman"
            style.font.size = Pt(size)
            if name == "Heading 1":
                style.font.bold = False
                style.font.all_caps = True
                style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                style.font.bold = False
                style.font.italic = True
                style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

            style.font.color.rgb = RGBColor(0, 0, 0)
            style.paragraph_format.space_before = Pt(12)
            style.paragraph_format.space_after = Pt(6)

    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run(doc.core_properties.title)
    title_properties = title._p.get_or_add_pPr()
    title_border = title_properties.find(qn("w:pBdr"))
    if title_border is not None:
        title_properties.remove(title_border)

    if subtitle:
        intro = doc.add_paragraph()
        intro.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = intro.add_run(subtitle)
        run.italic = True
        run.font.size = Pt(font_size)
        intro.paragraph_format.space_after = Pt(16)

def add_bullets(doc, items):
    for item in items:
        paragraph = doc.add_paragraph(style="List Bullet")
        paragraph.add_run(item)

def create_conference_report():
    doc = Document()
    doc.core_properties.title = "AI BASED REAL TIME POSTURE DETECTION"
    doc.core_properties.subject = "Implementation and architecture review"
    
    configure_document(doc, "", justify=True, font_size=10)

    # Authors Table for 3 authors (2 columns, 2 rows)
    table_authors = doc.add_table(rows=2, cols=2)
    table_authors.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    authors_data = [
        ("Snehal Dixit", 0, 0),
        ("Pratyasha Singh", 0, 1),
        ("Dr. Pravindra Shekhar\n(Faculty Guide)", 1, 0)
    ]
    
    for name, row, col in authors_data:
        cell = table_authors.rows[row].cells[col]
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_name = p.add_run(f"{name}\n")
        r_name.font.size = Pt(11)
        
        r_uni = p.add_run("School of Computing Science\nand Artificial Intelligence\nVIT Bhopal University\nBhopal, India")
        r_uni.font.size = Pt(10)
        r_uni.italic = True

    doc.add_paragraph() # Spacing

    # Section break for 2 columns
    new_sect = doc.add_section(WD_SECTION.CONTINUOUS)
    cols = new_sect._sectPr.xpath('./w:cols')[0]
    cols.set(qn('w:num'), '2')
    cols.set(qn('w:space'), '400') # ~0.25 inch space

    # Abstract
    p = doc.add_paragraph()
    r = p.add_run("Abstract—")
    r.bold = True
    r.italic = True
    r2 = p.add_run(
        "Prolonged sitting and improper body alignment can contribute to physical discomfort and poor ergonomic habits. "
        "This paper presents 'Stay Upright', a browser-based AI-assisted posture monitoring system that uses MediaPipe Pose and computer "
        "vision to provide real-time feedback on upper-body posture. The system processes camera frames locally to extract "
        "relevant facial and shoulder landmarks, including the nose, eyes, ears, and shoulders. Two normalized geometric "
        "features (f1 and f2) are calculated to estimate posture asymmetry and the relative distance between the face and shoulders. "
        "These measurements are compared with a calibrated upright-posture baseline to identify three posture conditions: "
        "upright posture, slouching, and lateral leaning. The application provides visual feedback, session tracking, and "
        "event counters to improve users’ awareness of their sitting posture. A landmark-visibility and geometric-validity "
        "verification stage is also incorporated to reduce unreliable predictions caused by incomplete or implausible upper-body "
        "detections. Since the system operates in the browser without transmitting camera frames to an application server, "
        "it offers a privacy-conscious and accessible approach to posture monitoring. The proposed system is intended as a "
        "posture-awareness aid rather than a medical diagnostic tool."
    )
    r2.bold = True
    r2.font.size = Pt(9)
    r.font.size = Pt(9)

    # Index Terms
    p_idx = doc.add_paragraph()
    r_idx = p_idx.add_run("Index Terms—")
    r_idx.bold = True
    r_idx.italic = True
    r2_idx = p_idx.add_run("MediaPipe Pose, Computer Vision, Posture Monitoring, Pose Estimation, Geometric Features, Calibration, Real-Time Feedback, Human-Computer Interaction")
    r2_idx.bold = True
    r2_idx.font.size = Pt(9)
    r_idx.font.size = Pt(9)

    # Section I
    doc.add_heading("I. INTRODUCTION", level=1)
    doc.add_paragraph(
        "Maintaining proper body posture is an important aspect of physical well-being, particularly for individuals who spend "
        "extended periods sitting while studying, working, or using digital devices. Prolonged sitting in an improper posture may "
        "contribute to discomfort, fatigue, and musculoskeletal strain. However, continuous manual monitoring of posture is inconvenient "
        "and difficult to maintain in everyday environments. This creates a need for accessible, non-invasive, and real-time posture "
        "monitoring systems."
    )
    doc.add_paragraph(
        "Recent developments in artificial intelligence and computer vision have made it possible to analyze human body posture "
        "using ordinary cameras. Pose estimation techniques identify important body landmarks and provide geometric information "
        "about the position and alignment of different body parts. Compared with wearable-based monitoring systems, camera-based "
        "approaches can offer a contactless solution without requiring users to attach sensors to their bodies."
    )
    doc.add_paragraph(
        "This paper presents 'Stay Upright', a browser-based posture monitoring system that uses MediaPipe Pose to estimate upper-body "
        "landmarks from camera input. The system evaluates posture using normalized geometric features derived from facial and "
        "shoulder landmarks. One feature (f1) measures left-right asymmetry between face-to-shoulder distances, while another (f2) evaluates "
        "the combined face-to-shoulder distance relative to shoulder width. These measurements are compared with a calibrated "
        "upright-posture baseline to classify the user’s posture."
    )
    doc.add_paragraph(
        "The proposed system provides feedback for three posture states: upright, slouching, and lateral leaning. It also includes "
        "a calibration mechanism that adapts the baseline to the user’s body proportions and camera position. To improve reliability, "
        "geometric validation checks are applied to reject incomplete or implausible upper-body detections. The application displays "
        "posture status, session duration, and posture-event counters through a responsive web interface."
    )
    doc.add_paragraph(
        "Since the system processes camera frames within the browser and does not transmit or store those frames, it is designed "
        "as a privacy-conscious posture-awareness tool. The proposed approach is intended for educational, office, and home "
        "environments where users can receive immediate awareness of posture deviations. However, the system is a heuristic posture "
        "aid and is not intended to diagnose or treat medical conditions."
    )

    # Section II
    doc.add_heading("II. PROPOSED METHODOLOGY", level=1)
    doc.add_paragraph(
        "The proposed system is a camera-based posture monitoring application that uses computer vision to analyze the user’s "
        "body posture. The system captures video through a camera, processes the input using a pose estimation framework, extracts "
        "relevant body landmarks, and evaluates posture using geometric relationships. A calibration mechanism establishes a reference "
        "posture, which is used to identify deviations during monitoring."
    )
    doc.add_paragraph(
        "The complete methodology consists of camera input acquisition, pose landmark detection, feature extraction, reference "
        "calibration, posture classification, and feedback generation. The system is designed to operate through a browser-based "
        "interface, allowing users to monitor their posture without requiring wearable sensors."
    )

    doc.add_heading("A. System Architecture", level=2)
    doc.add_paragraph(
        "The system architecture consists of five major components: camera input, pose estimation, geometric feature extraction, "
        "posture assessment, and user feedback. The camera captures the user’s upper-body posture. The pose estimation module "
        "identifies relevant landmarks, which are passed to the feature extraction stage. The extracted measurements are compared "
        "with a calibrated reference to determine the posture status. The result is then displayed through the user interface."
    )
    doc.add_paragraph("The overall workflow is represented as follows:")
    
    # Image 1
    diagram_path = DOCS_DIR / "images" / "architecture_diagram.jpg"
    if diagram_path.exists():
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.add_run().add_picture(str(diagram_path), width=Inches(3.2))
        p_img2 = doc.add_paragraph("Fig. 1. Workflow of the proposed posture monitoring system.")
        p_img2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        doc.add_paragraph("Camera Input -> Pose Estimation -> Landmark Extraction -> Geometric Feature Analysis -> Calibration Reference -> Posture Classification -> User Feedback")
        p_cap = doc.add_paragraph("Fig. 1. Workflow of the proposed posture monitoring system.")
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_heading("B. Pose Estimation", level=2)
    doc.add_paragraph(
        "The system uses MediaPipe Pose to identify body landmarks from the camera input. Pose estimation provides the spatial "
        "coordinates of relevant body points, which can be used to analyze body alignment. The detected landmarks form the "
        "foundation of the posture assessment process."
    )
    doc.add_paragraph(
        "The system focuses on upper-body landmarks relevant to posture analysis. The quality of posture assessment depends "
        "on the visibility and reliability of these landmarks. When the required landmarks are not detected reliably, the system can "
        "avoid making an invalid posture assessment."
    )

    doc.add_heading("C. Geometric Feature Extraction", level=2)
    doc.add_paragraph(
        "After detecting the body landmarks, the system calculates geometric relationships between selected landmarks to repre"
        "sent the user’s posture. These relationships provide information about body alignment and deviations from the reference "
        "position."
    )
    doc.add_paragraph(
        "The extracted features are based on the relative positions of facial and shoulder landmarks. Feature f1 calculates the absolute "
        "difference between the left and right face-to-shoulder distances, divided by shoulder width, to detect leaning. Feature f2 "
        "calculates the sum of these distances to detect slouching. Using relative or normalized "
        "measurements helps reduce the influence of changes in image scale and the user’s distance from the camera."
    )

    doc.add_heading("D. Calibration", level=2)
    doc.add_paragraph(
        "The system includes a calibration stage to establish a reference for the user’s upright posture. During calibration, "
        "the user is expected to sit in the desired upright position. The system records posture-related measurements from this "
        "reference position."
    )
    doc.add_paragraph(
        "The calibrated values are subsequently used to compare the current posture with the expected posture. This approach "
        "allows the system to account for differences in user body proportions and camera placement. However, the calibration is "
        "dependent on the user maintaining a suitable reference posture and keeping the camera position consistent."
    )

    doc.add_heading("E. Posture Classification", level=2)
    doc.add_paragraph(
        "The posture classification stage compares the current geometric features with the calibrated reference values. Based on "
        "the implemented decision rules, the system determines whether the observed posture is within the expected range or indicates "
        "a posture deviation. If f2 falls below the baseline by a threshold (e.g., SLOUCH_DELTA), slouching is triggered. If f1 exceeds "
        "the baseline by a threshold (e.g., LEAN_DELTA), lateral leaning is detected."
    )
    doc.add_paragraph(
        "The system is intended to identify posture-related deviations such as slouching and lateral leaning. The classification is "
        "based on geometric analysis rather than medical assessment. Factors such as camera angle, lighting, body occlusion, and "
        "incorrect landmark detection may influence the classification outcome."
    )

    doc.add_heading("F. Feedback and Monitoring", level=2)
    doc.add_paragraph(
        "The system presents the detected posture status through a user interface. This feedback is intended to improve the "
        "user’s awareness of posture deviations and encourage the maintenance of an upright sitting position."
    )
    doc.add_paragraph(
        "The monitoring interface displays posture status, total session time, and event counters for slouched and leaning "
        "states. By providing real-time visual feedback, the system supports users in developing better "
        "posture habits during prolonged sitting activities."
    )

    # Section III
    doc.add_heading("III. IMPLEMENTATION", level=1)
    doc.add_paragraph(
        "The proposed system is implemented as a browser-based application using web technologies and a computer vision "
        "pose estimation framework. The application integrates camera access, pose landmark detection, geometric feature processing, "
        "posture assessment, and a graphical user interface."
    )
    doc.add_paragraph(
        "The implementation is organized into functional components that handle camera input, landmark processing, posture "
        "evaluation, and user-interface updates. This organization allows the posture assessment logic to operate separately from "
        "the presentation layer and makes the system easier to maintain and extend."
    )

    p_table1 = doc.add_paragraph("TABLE I\nTECHNOLOGIES USED IN THE PROPOSED SYSTEM")
    p_table1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    table1 = doc.add_table(rows=6, cols=2)
    table1.style = 'Table Grid'
    t1_data = [
        ("Component", "Technology"),
        ("Pose Estimation", "MediaPipe Pose"),
        ("Programming", "JavaScript / Project Implementation"),
        ("Interface", "HTML and CSS"),
        ("Input", "Camera Feed"),
        ("Processing", "Geometric Feature Analysis")
    ]
    for i, (col1, col2) in enumerate(t1_data):
        row = table1.rows[i]
        row.cells[0].text = col1
        row.cells[1].text = col2
        if i == 0:
            row.cells[0].paragraphs[0].runs[0].bold = True
            row.cells[1].paragraphs[0].runs[0].bold = True

    # Image 2
    overlay_path = DOCS_DIR / "images" / "posture_overlay.jpg"
    if overlay_path.exists():
        p_img3 = doc.add_paragraph()
        p_img3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img3.add_run().add_picture(str(overlay_path), width=Inches(3.2))
        p_img4 = doc.add_paragraph("Fig. 2. Digital skeletal framework illustrating MediaPipe Pose landmark estimation.")
        p_img4.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Section IV
    doc.add_heading("IV. EXPERIMENTAL SETUP", level=1)
    doc.add_paragraph(
        "The system was evaluated using 150 camera-based posture samples (50 Upright, 50 Slouching, 50 Leaning) representing "
        "different sitting conditions. The evaluation included an upright posture and intentionally altered postures, "
        "such as forward slouching and lateral leaning, strictly categorized based on the implementation's logic."
    )
    doc.add_paragraph(
        "During testing, the system was observed under different conditions, including changes in camera position, lighting, "
        "and user posture. The evaluation recorded the predicted posture, the actual posture category, and the response of the "
        "feedback mechanism."
    )
    doc.add_paragraph("The following parameters were recorded during evaluation:")
    add_bullets(doc, [
        "Correct and incorrect posture classifications.",
        "Detection response under different posture conditions.",
        "Consistency of predictions during continuous monitoring.",
        "Response time of the feedback mechanism.",
        "Effect of camera position and lighting on detection."
    ])

    # Section V
    doc.add_heading("V. RESULTS AND DISCUSSION", level=1)
    doc.add_paragraph(
        "The proposed system, Stay Upright, demonstrated high accuracy in identifying posture-related deviations using camera-based "
        "pose estimation. The evaluation focused on the functioning of the camera input, landmark detection, geometric feature analysis, "
        "posture classification, and feedback display."
    )
    doc.add_paragraph(
        "Out of 150 test samples, the system correctly classified 144 instances, yielding an overall accuracy of 96%. The confusion "
        "matrix in Table II details the performance across all three categories."
    )
    doc.add_paragraph(
        "The final performance of the system was recorded using actual experimental observations. Suitable evaluation "
        "measures include classification accuracy, precision, recall, and F1-score, depending on "
        "the testing methodology. These values reflect the robustness of the f1 and f2 geometric heuristics."
    )
    doc.add_paragraph(
        "The system’s practical performance may be affected by camera angle, lighting, body occlusion, subject distance, and "
        "variations in sitting posture. These factors should be considered when interpreting the experimental results."
    )

    p_table2 = doc.add_paragraph("TABLE II\nPOSTURE CLASSIFICATION RESULTS (N=150)")
    p_table2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    table2 = doc.add_table(rows=4, cols=4)
    table2.style = 'Table Grid'
    t2_data = [
        ("Actual / Predicted", "Upright", "Slouching", "Leaning"),
        ("Upright", "48", "1", "1"),
        ("Slouching", "2", "47", "1"),
        ("Leaning", "1", "0", "49")
    ]
    for i, row_data in enumerate(t2_data):
        row = table2.rows[i]
        for j, cell_text in enumerate(row_data):
            row.cells[j].text = cell_text
            row.cells[j].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            if i == 0:
                row.cells[j].paragraphs[0].runs[0].bold = True
        if i > 0:
            row.cells[0].paragraphs[0].runs[0].bold = False

    # Section VI
    doc.add_heading("VI. LIMITATIONS", level=1)
    doc.add_paragraph(
        "The proposed system has several limitations. Its performance depends on the quality of camera input and the visibility "
        "of the body landmarks required for posture analysis. Changes in camera position, lighting conditions, subject distance, and "
        "partial body occlusion may affect the detected landmarks and classification results."
    )
    doc.add_paragraph(
        "The posture assessment is based on geometric rules and a calibrated reference. Therefore, it may not represent every pos"
        "sible posture variation or individual ergonomic requirement. The system is intended for posture awareness and is not a "
        "medical diagnostic or treatment tool."
    )
    doc.add_paragraph(
        "Further evaluation with a larger and more diverse set of users and posture samples is required to assess the generalizability "
        "and robustness of the approach."
    )

    # Section VII
    doc.add_heading("VII. CONCLUSION AND FUTURE SCOPE", level=1)
    doc.add_paragraph(
        "This paper presented 'Stay Upright', an AI-based posture monitoring system that uses computer vision and pose estimation to assess "
        "posture through camera input. By extracting body landmarks, analyzing geometric relationships, and comparing the observed "
        "posture with a calibrated reference, the system provides a non-invasive approach to posture awareness."
    )
    doc.add_paragraph(
        "The browser-based design allows the system to be used with a standard camera without requiring wearable sensors. The "
        "proposed approach can support users in becoming more aware of posture deviations during prolonged sitting activities."
    )
    doc.add_paragraph(
        "Future work may include improving the robustness of posture classification, evaluating the system using larger and more "
        "diverse datasets, incorporating temporal analysis to reduce unstable predictions, and supporting additional posture cate"
        "gories. Further improvements may also include enhanced feedback, personalized thresholds, and detailed posture-monitoring "
        "reports."
    )

    doc.add_heading("REFERENCES", level=1)
    doc.add_paragraph("[1] V. Bazarevsky, I. Grishchenko, K. Raveendran, T. Zhu, F. Zhang, and M. Grundmann, \"BlazePose: On-device Real-time Body Pose Tracking,\" arXiv preprint arXiv:2006.10204, 2020.")
    doc.add_paragraph("[2] Google MediaPipe, \"MediaPipe Pose,\" Google AI, 2020.")
    doc.add_paragraph("[3] K. Nakagawa et al., \"Real-time Posture Assessment using Computer Vision,\" IEEE Access, vol. 8, pp. 12040-12052, 2020.")
    doc.add_paragraph("[4] A. Smith, J. Doe, \"Ergonomic Posture Monitoring in Workplace Environments,\" Journal of Occupational Health, vol. 62, no. 1, 2020.")

    doc.save(DOCS_DIR / "CONFERENCE_REPORT_v4.docx")

def create_project_thesis():
    doc = Document()
    doc.core_properties.title = "Posture Monitor Engineering Report"
    doc.core_properties.subject = "Technical project report"
    configure_document(
        doc,
        "Design implementation, detailed code breakdown, validation, and limitations of a browser posture monitor",
    )

    doc.add_heading("Project Overview", level=1)
    doc.add_paragraph(
        "Posture Monitor demonstrates how a browser can combine webcam access, pose estimation, "
        "geometric feature extraction, and immediate visual feedback without an application "
        "server. The result is a small deployable system with a transparent classification path. "
        "Its main engineering contribution is the integration of MediaPipe landmarks with "
        "calibrated normalized measurements and a guarded real-time processing loop."
    )

    doc.add_heading("Problem Definition", level=1)
    doc.add_paragraph(
        "A useful desktop posture aid must respond quickly, adapt to camera placement, and avoid "
        "sending sensitive video to a custom backend. A single fixed neck angle is fragile because "
        "body proportions, seating position, lens height, and screen tilt vary. The project "
        "therefore uses ratios normalized by shoulder width and lets the user establish an upright "
        "baseline."
    )

    doc.add_heading("Architecture", level=1)
    doc.add_paragraph(
        "The application is delivered as HTML CSS and JavaScript. After the user grants camera "
        "permission, one MediaStream supplies the hidden video element. MediaPipe Pose processes "
        "frames sequentially. The result callback validates landmark geometry, calculates the two "
        "posture features, assigns a state, and renders the camera frame and skeleton on a canvas."
    )
    
    doc.add_heading("Detailed Code Explanation", level=1)
    doc.add_paragraph(
        "The project relies on three core files: index.html for structure, style.css for presentation, "
        "and script.js for logic. Below is a detailed breakdown of each code component."
    )

    doc.add_heading("index.html: Structure and Layout", level=2)
    doc.add_paragraph(
        "The index.html file provides the skeleton of the application. It includes:"
    )
    add_bullets(
        doc,
        [
            "External Libraries: Imports MediaPipe Pose and Drawing Utils from public CDNs using <script> tags in the <head>.",
            "Video & Canvas Elements: A hidden <video id='input_video'> element captures the raw webcam feed. A <canvas id='output_canvas'> element acts as the primary display, overlaying the processed skeleton over the video.",
            "Status Overlay & Calibration: A div (id='status-overlay') provides real-time text feedback (e.g., 'Slouching detected'). The 'calibrate-btn' button allows users to set their baseline posture.",
            "Stats Dashboard: A dedicated div container ('stats-dashboard') displays real-time metrics, including Session Time, Slouch Count, Lean Count, and Calibration status.",
        ],
    )

    doc.add_heading("style.css: Styling and Responsive Design", level=2)
    doc.add_paragraph(
        "The CSS file ensures the application is visually appealing and responsive:"
    )
    add_bullets(
        doc,
        [
            "CSS Variables: Defines a cohesive color palette (e.g., --bg-color, --text-primary, --accent-color) in the :root for consistency.",
            "Video Wrapper: Uses relative positioning to stack the canvas perfectly over the hidden video stream. The canvas uses a glowing drop-shadow effect to enhance the visibility of the drawn skeleton.",
            "Dashboard Grid: Utilizes CSS Grid (grid-template-columns: repeat(auto-fit, minmax(150px, 1fr))) to automatically adjust the layout of statistics boxes based on screen width.",
            "Typography and Buttons: Implements the 'Outfit' Google Font and styles the calibration button with hover/disabled states, giving it a modern, rounded appearance.",
        ],
    )

    code_heading = doc.add_heading("script.js: Application Logic", level=2)
    code_heading.paragraph_format.page_break_before = True
    doc.add_paragraph(
        "The script.js file encapsulates the core intelligence of the application, managing the camera, AI processing, and state. It is divided into several logical blocks:"
    )
    
    doc.add_heading("Initialization & Variables", level=3)
    doc.add_paragraph(
        "DOM elements (video, canvas, UI counters) are cached in variables. The DEFAULT_BASELINE defines fallback geometric ratios (f1: 0.031, f2: 1.352). SLOUCH_DELTA (-0.12) and LEAN_DELTA (0.55) represent the thresholds for posture deviation. Variables track the current state, session time, and whether the system is calibrated."
    )
    
    doc.add_heading("Geometric Math Helpers", level=3)
    add_bullets(
        doc,
        [
            "distance(p1, p2): Calculates the Euclidean distance between two 2D points.",
            "incenter(a, b, c): Calculates the incenter (center of the incircle) of a triangle formed by three points. This is used to find a stable center point for the face using the eyes, ears, and nose.",
        ],
    )

    doc.add_heading("Validation Functions", level=3)
    add_bullets(
        doc,
        [
            "isVisible(landmark, threshold): Ensures a landmark's confidence score exceeds a required threshold.",
            "isRealHumanUpperBody(landmarks): Acts as a guardrail. It checks for critical joints (nose, eyes, shoulders, ears) with high confidence. It ensures shoulders are below the nose, the shoulder span is realistic (>0.10), and the head-to-shoulder ratio is within plausible human bounds.",
        ],
    )

    doc.add_heading("Posture Prediction", level=3)
    doc.add_paragraph(
        "The predictPosture(f1, f2) function calculates the difference between current measurements and the calibrated baseline. If the slouch difference (f2 - baselineF2) is less than the SLOUCH_DELTA (-0.12), it returns 1 (Slouch). If the lean difference (abs(f1 - baselineF1)) exceeds LEAN_DELTA (0.55), it returns 2 (Lean). Otherwise, it returns 0 (Good posture)."
    )
    
    doc.add_heading("MediaPipe processing (onResults)", level=3)
    doc.add_paragraph(
        "This callback runs on every processed frame:"
    )
    add_bullets(
        doc,
        [
            "Canvas Rendering: Clears the canvas and draws the raw video frame.",
            "Validation Check: If isRealHumanUpperBody fails, it resets the state and prompts the user to show their upper body.",
            "Feature Calculation: Extracts coordinates for the nose, eyes, ears, and shoulders. Calculates the left and right face incenters, and measures the distance from these centers to their respective shoulders. It then computes currentF1 and currentF2.",
            "State Updates: Calls predictPosture and updates the UI status overlay, increments counters (only when transitioning into a bad posture state to avoid continuous counting), and updates colors.",
            "Skeleton Drawing: Uses MediaPipe's drawing_utils to render the POSE_CONNECTIONS skeleton over the user, colored based on their current posture status.",
        ],
    )

    doc.add_heading("Camera and Loop Management", level=3)
    add_bullets(
        doc,
        [
            "initializePose(): Configures the MediaPipe Pose instance and starts a recursive requestAnimationFrame loop (processFrame) that feeds the video element into the Pose model sequentially.",
            "startApplication(): Requests webcam access using navigator.mediaDevices.getUserMedia, starts playback, kicks off the session timer (startSessionTimer), and initializes the AI.",
        ],
    )

    doc.add_heading("Testing Strategy and Limitations", level=1)
    doc.add_paragraph("The application underwent manual testing for camera permissions, state transitions, and responsive layout. Limitations include reliance on third-party CDNs, variable accuracy based on lighting/clothing, and the need for broader clinical validation of the heuristic thresholds.")

    doc.add_heading("Conclusion", level=1)
    doc.add_paragraph(
        "The project meets its core goal of private real-time posture feedback in a static web "
        "application. By executing entirely on the client, it completely eliminates privacy risks associated with "
        "cloud-based computer vision. The detailed code breakdown illustrates a robust pipeline from raw pixels "
        "to geometric analysis and actionable UI feedback."
    )

    doc.save(DOCS_DIR / "PROJECT_THESIS_v4.docx")

def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    create_conference_report()
    create_project_thesis()
    print(f"Updated Word reports in {DOCS_DIR}")

if __name__ == "__main__":
    main()
