def authorized_to_manage_request(_, request, current_user, pushmaster=False):
    if pushmaster or \
       request['user'] == current_user or \
       (request['watchers'] and current_user in request['watchers'].split(',')):
        return True
    return False
