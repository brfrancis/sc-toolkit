from flask import Blueprint, request, render_template


demo_bp = Blueprint('demo_bp', __name__, url_prefix='/demo')


@demo_bp.route('')
def demo_index():
    return render_template('demo-landing-page/index.html', active='demo')


@demo_bp.route('/generate', methods=['POST'])
def demo_generate():
    from demo_landing_page.generator import generate
    client_name  = request.form.get('client_name', '')
    use_case     = request.form.get('use_case', '')
    stakeholder  = request.form.get('stakeholder', 'CUO')
    fields_raw   = request.form.get('fields', '')
    fields       = [f.strip() for f in fields_raw.splitlines() if f.strip()]

    use_case_labels = {
        'submission_triage':    'Submission triage',
        'bordereaux_processing':'Bordereaux processing',
        'claims_automation':    'Claims automation',
        'da_workflows':         'DA workflows',
    }
    stakeholder_values = {
        'CUO': 'Faster submission triage and improved risk selection through automated extraction and enrichment.',
        'COO': 'Reduced manual processing overhead and scalable ingestion without proportional headcount growth.',
        'CIO': 'API-first integration with existing underwriting systems, audit-ready outputs, and explainable AI.',
    }

    return render_template(
        'demo-landing-page/result.html',
        active='demo',
        client_name=client_name,
        use_case_label=use_case_labels.get(use_case, use_case),
        stakeholder=stakeholder,
        fields=fields,
        stakeholder_value=stakeholder_values.get(stakeholder, ''),
    )
