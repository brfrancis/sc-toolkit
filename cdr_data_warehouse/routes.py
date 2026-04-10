from flask import Blueprint, request, render_template
import traceback


cdr_bp = Blueprint('cdr_bp', __name__, url_prefix='/cdr')


@cdr_bp.route('')
def cdr_index():
    return render_template(
        'cdr-data-warehouse/index.html',
        active='cdr',
        selected_cluster='try.indico.io',
        submission_id='',
        execution_output='',
    )


@cdr_bp.route('/process', methods=['POST'])
def cdr_process():
    from cdr_data_warehouse.duckdb_demo import run_demo
    selected_cluster = request.form.get('cluster', 'try.indico.io').strip() or 'try.indico.io'
    submission_id = request.form.get('submission_id', '').strip()
    try:
        execution_output = run_demo()
    except Exception as e:
        execution_output = f"Execution failed: {e}\n\n{traceback.format_exc()}"

    return render_template(
        'cdr-data-warehouse/index.html',
        active='cdr',
        selected_cluster=selected_cluster,
        submission_id=submission_id,
        execution_output=execution_output,
    )
