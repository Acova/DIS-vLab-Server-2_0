from app.core import app, celery
from app.api.utils import json_response, token_required


@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    task = celery.AsyncResult(task_id)
    state = task.state
    if state == "SUCCESS":
        return json_response(data={
            'status': 0,
            'return_value': task.get()
        })
    elif state == "FAILURE":
        return json_response(data={
            'status': -1
        })
    else:
        return json_response(data={
            'status': 1
        })
