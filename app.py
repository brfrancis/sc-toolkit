from flask import Flask, request, render_template, redirect, url_for, jsonify
import git
import hmac
import hashlib
import os
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

app = Flask(__name__)


# ── Webhook — GitHub → PythonAnywhere auto-deploy ─────────────────────────
@app.route('/update_server', methods=['POST'])
def webhook():
    if request.method != 'POST':
        return 'Wrong event type', 400
    secret = os.environ.get('WEBHOOK_SECRET', '').encode()
    signature = request.headers.get('X-Hub-Signature', '')
    mac = hmac.new(secret, msg=request.data, digestmod=hashlib.sha1)
    if not hmac.compare_digest('sha1=' + mac.hexdigest(), signature):
        return 'Invalid signature', 403
    repo = git.Repo('/home/brfrancis/sc-toolkit')
    repo.remotes.origin.pull()
    return 'Updated successfully', 200


# ── Home ───────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


# ── Demo landing page ──────────────────────────────────────────────────────
@app.route('/demo')
def demo_index():
    return render_template('demo-landing-page/index.html', active='demo')


@app.route('/demo/generate', methods=['POST'])
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


# ── CDR data warehouse ─────────────────────────────────────────────────────
@app.route('/cdr')
def cdr_index():
    return render_template('cdr-data-warehouse/index.html', active='cdr')


@app.route('/cdr/process', methods=['POST'])
def cdr_process():
    from cdr_data_warehouse.pipeline import load_bronze, bronze_to_silver, silver_to_gold
    json_input   = request.form.get('json_input', '{}')
    threshold    = float(request.form.get('confidence_threshold', 0.75))
    submission_id = request.form.get('submission_id', 'SUB-001')

    try:
        data   = json.loads(json_input)
        bronze = load_bronze(data)
        silver = bronze_to_silver(bronze, confidence_threshold=threshold)
        gold   = silver_to_gold(silver)
    except NotImplementedError:
        bronze = []
        silver = []
        gold   = {"status": "Pipeline in development"}
    except Exception as e:
        bronze = []
        silver = []
        gold   = {"error": str(e)}

    return render_template(
        'cdr-data-warehouse/result.html',
        active='cdr',
        submission_id=submission_id,
        bronze=bronze.to_dict('records') if hasattr(bronze, 'to_dict') else bronze,
        silver=silver,
        gold=gold,
        threshold=threshold,
    )


# ── Use case intelligence ──────────────────────────────────────────────────
@app.route('/uci')
def uci_index():
    import csv, json as _json, os
    data_dir = os.path.join(os.path.dirname(__file__), 'usecase_intelligence', 'data')

    use_case_suffix = '_use_cases.csv'
    relationship_suffixes = ('_use_case_relationships.csv', '_relationships.csv')
    dataset_sources = {}

    for filename in os.listdir(data_dir):
        if not filename.endswith('.csv'):
            continue

        full_path = os.path.join(data_dir, filename)

        if filename.endswith(use_case_suffix):
            prefix = filename[:-len(use_case_suffix)]
            dataset_sources.setdefault(prefix, {})['use_cases_path'] = full_path
            continue

        for relationship_suffix in relationship_suffixes:
            if filename.endswith(relationship_suffix):
                prefix = filename[:-len(relationship_suffix)]
                dataset_sources.setdefault(prefix, {})['relationships_path'] = full_path
                break

    dataset_options = []
    for prefix, paths in dataset_sources.items():
        if 'use_cases_path' not in paths or 'relationships_path' not in paths:
            continue
        dataset_options.append({
            'prefix': prefix,
            'label': prefix.replace('_', ' ').strip(),
            'use_cases_path': paths['use_cases_path'],
            'relationships_path': paths['relationships_path'],
        })

    dataset_options.sort(key=lambda d: d['label'].lower())
    if not dataset_options:
        return render_template(
            'usecase-intelligence/index.html',
            active='uci',
            functions=[],
            graph_json=_json.dumps({'nodes': [], 'edges': []}),
            node_count=0,
            edge_count=0,
            dataset_options=[],
            selected_dataset=None,
        )

    requested_dataset = (request.args.get('dataset') or '').strip()
    selected_option = next((d for d in dataset_options if d['prefix'] == requested_dataset), None)
    if not selected_option:
        selected_option = next((d for d in dataset_options if d['prefix'] == 'Alteryx'), dataset_options[0])

    nodes = []
    seen_node_ids = set()
    functions = set()
    with open(selected_option['use_cases_path']) as f:
        for row in csv.DictReader(f):
            node_id = row['Use Case']
            if node_id in seen_node_ids:
                continue
            seen_node_ids.add(node_id)
            description = (row.get('Description') or '').strip()
            nodes.append({
                'id': node_id,
                'function': row['Function'],
                'department': row['Department'],
                'description': description if description else '--',
            })
            functions.add(row['Function'])
    
    edges = []
    with open(selected_option['relationships_path']) as f:
        for row in csv.DictReader(f):
            source = row['From Use Case']
            target = row['To Use Case']
            if source not in seen_node_ids or target not in seen_node_ids:
                continue
            edges.append({'source': row['From Use Case'], 'target': row['To Use Case'], 'scope': row['Relationship Scope']})
    
    graph_json = _json.dumps({'nodes': nodes, 'edges': edges})
    functions_list = sorted(functions)
    
    return render_template(
        'usecase-intelligence/index.html',
        active='uci',
        functions=functions_list,
        graph_json=graph_json,
        node_count=len(nodes),
        edge_count=len(edges),
        dataset_options=[{'prefix': d['prefix'], 'label': d['label']} for d in dataset_options],
        selected_dataset=selected_option['prefix'],
    )


@app.route('/uci/logo-search')
def uci_logo_search():
    query = (request.args.get('query') or '').strip()
    if not query:
        return jsonify({'results': []})

    params = urlencode({
        'action': 'query',
        'format': 'json',
        'generator': 'search',
        'gsrsearch': f'{query} company logo',
        'gsrlimit': 6,
        'prop': 'pageimages|info',
        'piprop': 'thumbnail',
        'pithumbsize': 160,
        'inprop': 'url',
        'origin': '*',
    })
    wiki_url = f'https://en.wikipedia.org/w/api.php?{params}'

    try:
        req = Request(wiki_url, headers={'User-Agent': 'sc-toolkit/1.0 (logo-search)'})
        with urlopen(req, timeout=6) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except Exception:
        return jsonify({'results': []})

    pages = list((payload.get('query') or {}).get('pages', {}).values())
    pages.sort(key=lambda page: int(page.get('index', 9999)))

    results = []
    seen = set()
    for page in pages:
        logo = (page.get('thumbnail') or {}).get('source')
        title = (page.get('title') or '').strip()
        if not logo or not title:
            continue
        key = (title.lower(), logo)
        if key in seen:
            continue
        seen.add(key)
        results.append({'name': title, 'logo': logo})
        if len(results) >= 5:
            break

    return jsonify({'results': results})




@app.route('/uci/classify', methods=['POST'])
def uci_classify():
    from usecase_intelligence.classifier import classify
    from usecase_intelligence.network    import recommend, get_network_json

    name        = request.form.get('use_case_name', '')
    description = request.form.get('description', '')
    implemented = json.loads(request.form.get('implemented', '[]'))
    veto        = json.loads(request.form.get('veto', '[]'))

    try:
        result = classify(name, description)
    except Exception as e:
        result = {'primary': str(e), 'challenger': None, 'agreed': None, 'final': str(e), 'confidence': None}

    recommendations = recommend(
        implemented=implemented,
        veto=veto,
        interested=[result['final']] if result.get('final') else [],
    ) if implemented else []

    network_json = json.dumps(
        get_network_json(implemented, veto, recommendations)
    )

    return render_template(
        'usecase-intelligence/result.html',
        active='uci',
        result=result,
        recommendations=recommendations,
        network_json=network_json,
    )


if __name__ == '__main__':
    app.run(debug=True)
