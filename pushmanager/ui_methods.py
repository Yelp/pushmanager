def authorized_to_manage_request(_, request, current_user, pushmaster=False):
    if pushmaster or \
       request['user'] == current_user or \
       (request['watchers'] and current_user in request['watchers'].split(',')):
        return True
    return False

def sort_pickmes(_, requests, tags_order):
    """Sort pickmes based on tags_order

    Args:
    -          - request handler object
    requests   - a list of requests
    tags_order - order to sort requests

    Return: sorted requests list
    """

    def compare_tags(tags1, tags2):
        tags1_list = tags1.split(',')
        tags2_list = tags2.split(',')

        for tag in tags_order:
            tag_in_tags1 = tag in tags1_list
            tag_in_tags2 = tag in tags2_list
            if tag_in_tags1 == tag_in_tags2:
                continue
            elif tag_in_tags1:
                return -1
            else:
                return 1
        return 0

    sorted_requests = sorted(requests, key=lambda req: req['tags'], cmp=compare_tags)
    return sorted_requests
