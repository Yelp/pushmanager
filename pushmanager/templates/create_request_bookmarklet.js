(function() {
    Settings = {{ JSSettings_json }};

    var ticketNumberToURL = function(bug) {
        return Settings['ticket_tracker_url_format'].replace("%TICKET%", bug);
    };

    var summary = $('#field_summary').text();
    var codeReview = location.href.split('#')[0];
    var reviewid = codeReview.match(/\d+/)[0];
    var tickets = $('#field_bugs_closed').text().split(',').filter(Boolean).map(ticketNumberToURL);
    var description = summary + '\n\n' + $('#field_description').text();

    // Get a list of reviewers who have a 'Ship it!', filtering out dupes
    var reviewerSet = {};
    var reviewers = $('div.shipit ~ div.reviewer > a').map(function() {
        var reviewer = $.trim(this.text);
        if (reviewer && !reviewerSet[reviewer]) {
            reviewerSet[reviewer] = true;
            return reviewer;
        }
    }).get();

    var branch = $('#field_branch').text();
    var repo = Settings['git']['main_repository'];
    if(branch.indexOf('/') != -1) {
        var branchparts = branch.split('/', 2);
        repo = branchparts[0];
        branch = branchparts[1];
    }

    var comments = [];
    if (reviewers.length > 0) {
        comments.push('SheepIt from ' + reviewers.join(', '));
    }
    if (tickets.length > 0) {
        comments.push((tickets.length == 1 ? 'Ticket: ' : 'Tickets: ') + tickets.join(' '));
    }
    comments = comments.join('\n\n');

    main_app_port = Settings['main_app']['port'] == 443 ? ':' + Settings['main_app']['port'] : '';

    location.href = 'https://' + Settings['main_app']['servername'] + main_app_port + '/requests?' + $.param({
        'bookmarklet': 1,
        'title': summary,
        'repo': repo,
        'branch': branch,
        'review': reviewid,
        'comments': comments,
        'description': description
    });
})();
