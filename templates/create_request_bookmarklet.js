(function() {
    Settings = {{ JSSettings_json }};

    var ticketNumberToURL = function(bug) {
        return 'https://' + Settings['trac']['servername'] + '/ticket/' + bug.match(/\d+/)[0];
    };

    var summary = $('#summary').text();
    var codeReview = location.href.split('#')[0];
    var reviewid = codeReview.match(/\d+/)[0];
    var tickets = $('#bugs_closed').text().split(',').filter(Boolean).map(ticketNumberToURL);
    var description = summary + '\n' + $('#description').text();

    // Get a list of reviewers who have a 'Ship it!', filtering out dupes
    var reviewerSet = {};
    var reviewers = $('div.shipit ~ div.reviewer > a').map(function() {
        var reviewer = $.trim(this.text);
        if (reviewer && !reviewerSet[reviewer]) {
            reviewerSet[reviewer] = true;
            return reviewer;
        }
    }).get();

    var branch = $('#branch').text();
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

    location.href = 'https://' + Settings['main_app']['servername'] + '/requests?' + $.param({
        'bookmarklet': 1,
        'title': summary,
        'repo': repo,
        'branch': branch,
        'review': reviewid,
        'comments': comments,
        'description': description
    });
})();
