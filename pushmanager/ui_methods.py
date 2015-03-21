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

    def compare_requests(request1, request2):
        tags1_list = request1['tags'].split(',')
        tags2_list = request2['tags'].split(',')

        for tag in tags_order:
            tag_in_tags1 = tag in tags1_list
            tag_in_tags2 = tag in tags2_list
            if tag_in_tags1 == tag_in_tags2:
                continue
            elif tag_in_tags1:
                return -1
            else:
                return 1

        return cmp(request1['user'], request2['user'])

    sorted_requests = sorted(requests, cmp=compare_requests)
    return sorted_requests
