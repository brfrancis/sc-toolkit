from flask import Flask, request, render_template
import git
import hmac
import hashlib
import os

from demo_landing_page.routes import demo_bp
from cdr_data_warehouse.routes import cdr_bp
from usecase_intelligence.routes import uci_bp
from workflow_builder.routes import workflow_bp


def create_app():
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

    app.register_blueprint(demo_bp)
    app.register_blueprint(cdr_bp)
    app.register_blueprint(uci_bp)
    app.register_blueprint(workflow_bp)

    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug=True)
