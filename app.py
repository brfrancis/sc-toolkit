from flask import Flask, request, render_template, redirect, url_for, jsonify
import git
import hmac
import hashlib
import os
import json
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import re
import html

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
    request_timeout = 3
    query = (request.args.get('query') or '').strip()
    if not query:
        return jsonify({'results': []})

    api_key = os.environ.get('GOOGLE_CSE_API_KEY', '').strip()
    cse_id = os.environ.get('GOOGLE_CSE_ID', '').strip()

    issues = []

    # Preferred route: official Google Custom Search JSON API (image search mode).
    if api_key and cse_id:
        params = urlencode({
            'key': api_key,
            'cx': cse_id,
            'q': f'{query} official logo',
            'searchType': 'image',
            'safe': 'active',
            'num': 10,
            'imgSize': 'medium',
            'rights': 'cc_publicdomain,cc_attribute',
        })
        api_url = f'https://customsearch.googleapis.com/customsearch/v1?{params}'
        try:
            req = Request(api_url, headers={'User-Agent': 'sc-toolkit/1.0 (google-image-search)'})
            with urlopen(req, timeout=request_timeout) as response:
                payload = json.loads(response.read().decode('utf-8'))

            items = payload.get('items', [])
            results = []
            for item in items:
                image_data = item.get('image') or {}
                full_image = item.get('link') or ''
                logo_url = image_data.get('thumbnailLink') or full_image
                source = (item.get('displayLink') or '').lower()
                title = (item.get('title') or '').lower()

                if not logo_url:
                    continue
                if any(noise in title for noise in ['tower', 'building', 'headquarters', 'office', 'seamless']):
                    continue

                results.append({
                    'name': item.get('title') or source or query,
                    'logo': logo_url,
                    'source': source,
                    'full_image': full_image or logo_url,
                })
                if len(results) >= 6:
                    break

            # If CSE credentials are valid but image filters are strict/noisy, fall through
            # to the scraper fallback instead of surfacing an unavailable state on the UI.
            if results:
                return jsonify({'results': results})
            issues.append('Google Custom Search returned no usable image results.')
        except HTTPError as err:
            api_error = f'Google Custom Search failed ({err.code}).'
            try:
                error_payload = json.loads(err.read().decode('utf-8', errors='ignore'))
                msg = ((error_payload.get('error') or {}).get('message') or '').strip()
                if msg:
                    api_error = f'{api_error} {msg}'
            except Exception:
                pass
            issues.append(api_error)
        except URLError:
            issues.append('Google Custom Search is unreachable from the server.')
        except Exception:
            issues.append('Google Custom Search failed unexpectedly.')
    else:
        missing = []
        if not api_key:
            missing.append('GOOGLE_CSE_API_KEY')
        if not cse_id:
            missing.append('GOOGLE_CSE_ID')
        issues.append(f"Google Custom Search credentials are missing ({', '.join(missing)}).")

    # Fallback: scrape Google Images HTML when API credentials are unavailable.
    search_query = f'{query} official logo'
    params = urlencode({'q': search_query, 'tbm': 'isch', 'hl': 'en', 'safe': 'active'})
    google_url = f'https://www.google.com/search?{params}'

    try:
        req = Request(google_url, headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/124.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        with urlopen(req, timeout=request_timeout) as response:
            page_html = response.read().decode('utf-8', errors='ignore')
    except Exception:
        issues.append('Google Images HTML fallback is unavailable (likely blocked/rate-limited).')
        page_html = ''

    patterns = [
        r'\"ou\":\"(https?://[^\"\\]+)\"',
        r'\\[\"(https?://[^\"\\]+)\",[0-9]+,[0-9]+\\]',
        r'\"(https?://[^\"\\]+(?:png|jpg|jpeg|webp|svg))\"',
    ]

    extracted = []
    for pattern in patterns:
        extracted.extend(re.findall(pattern, page_html))

    cleaned_urls = []
    seen = set()
    for raw_url in extracted:
        url = html.unescape(raw_url).replace('\\u003d', '=').replace('\\u0026', '&')
        if 'gstatic.com' in url or 'googleusercontent.com' in url:
            continue
        if not url.startswith('http'):
            continue
        if url in seen:
            continue
        seen.add(url)
        cleaned_urls.append(url)
        if len(cleaned_urls) >= 10:
            break

    results = []
    for url in cleaned_urls:
        host = (urlparse(url).netloc or '').replace('www.', '')
        results.append({
            'name': host or query,
            'logo': url,
            'source': host,
            'full_image': url,
        })
        if len(results) >= 6:
            break

    if results:
        return jsonify({'results': results})

    issues.append('Google Images fallback returned no usable image URLs.')

    # Last fallback: Wikipedia page images.
    wiki_params = urlencode({
        'action': 'query',
        'format': 'json',
        'generator': 'search',
        'gsrsearch': f'{query} logo',
        'gsrlimit': 8,
        'prop': 'pageimages|info',
        'inprop': 'url',
        'pithumbsize': 500,
        'origin': '*',
    })
    wiki_url = f'https://en.wikipedia.org/w/api.php?{wiki_params}'
    try:
        req = Request(wiki_url, headers={'User-Agent': 'sc-toolkit/1.0 (wikipedia-logo-fallback)'})
        with urlopen(req, timeout=request_timeout) as response:
            payload = json.loads(response.read().decode('utf-8'))

        wiki_results = []
        pages = (payload.get('query') or {}).get('pages') or {}
        for page in pages.values():
            thumb = (page.get('thumbnail') or {}).get('source')
            if not thumb:
                continue
            title = page.get('title') or query
            full_page = page.get('fullurl') or 'wikipedia.org'
            wiki_results.append({
                'name': title,
                'logo': thumb,
                'source': 'wikipedia.org',
                'full_image': thumb,
                'reference': full_page,
            })
            if len(wiki_results) >= 6:
                break

        if wiki_results:
            return jsonify({'results': wiki_results, 'fallback': 'wikipedia'})

        issues.append('Wikipedia fallback returned no image candidates.')
    except Exception:
        issues.append('Wikipedia fallback failed.')

    issue_text = ' | '.join(issues[-3:]) if issues else 'Unknown search issue.'
    return jsonify({'results': [], 'issue': issue_text}), 503




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
