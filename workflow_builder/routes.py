from flask import Blueprint, render_template, request

from workflow_builder.client import IntakeClient


workflow_bp = Blueprint('workflow_bp', __name__, url_prefix='/workflow-builder')
TOKEN_PATH = '/home/brfrancis/sc-toolkit/try_token.txt'


@workflow_bp.route('')
def workflow_index():
    return render_template(
        'workflow-builder/index.html',
        active='workflow',
        selected_cluster='try.indico.io',
        version_result=None,
        error_message='',
    )


@workflow_bp.route('/version', methods=['POST'])
def workflow_version():
    selected_cluster = request.form.get('cluster', 'try.indico.io').strip() or 'try.indico.io'

    try:
        client = IntakeClient(
            workflow_host=selected_cluster,
            workflow_token=TOKEN_PATH,
        )
        version_result = client.get_version()
        error_message = ''
    except Exception as exc:
        version_result = None
        error_message = str(exc)

    return render_template(
        'workflow-builder/index.html',
        active='workflow',
        selected_cluster=selected_cluster,
        version_result=version_result,
        error_message=error_message,
    )
