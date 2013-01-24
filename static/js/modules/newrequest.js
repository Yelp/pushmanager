$(function() {
    PushManager = window.PushManager || {};
    PushManager.NewRequestDialog = PushManager.NewRequestDialog || {};

    PushManager.NewRequestDialog.element = $('#create-new-request-dialog');
    PushManager.NewRequestDialog.element.dialog({
        autoOpen: false,
        title: 'Create/Edit Push Request',
        width: 650,
        minWidth: 650,
        height: 750,
        maxHeight: 750,
        minHeight: 750
    });

    PushManager.NewRequestDialog.validate = function() {
        var d = PushManager.NewRequestDialog.element;

        // Validate ReviewBoard ID
        if(!/^\d*$/.test(d.find('#request-form-review').val())) {
            alert("Invalid review # - only integer ReviewBoard IDs are allowed.");
            return false;
        }

        // Validate l10n-only request
        if(d.find('#request-form-tags').val().match('[ ]?l10n-only[ ]?') && d.find('#request-form-branch').val() !== '') {
            alert("l10n-only request should not have a branch. " +
                  "Use l10n request tag if you have a repository change to be pushed. " +
                  "Please remove l10n-only tag or branch name from your request.");
            return false;
        }

        return true;
    };
    $('#request-info-form').submit(PushManager.NewRequestDialog.validate);

    PushManager.NewRequestDialog.open_new_request = function(title, branch, repo, review, comments, description, tags, requestid, notyours) {
        var d = PushManager.NewRequestDialog.element;

        d.find('#request-form-title').val(title || '');
        d.find('#request-form-repo').val(repo || PushManager.current_user);
        d.find('#request-form-branch').val(branch || '');
        d.find('#request-form-review').val(review || '');
        d.find('#request-form-tags').val(tags || '');
        d.find('#request-form-comments').val(comments || '');
        d.find('#request-form-description').val(description || '');
        d.find('#request-form-id').val(requestid || '');
        d.find('#request-not-yours-notice').toggle(notyours || false);

        d.dialog('open');
    };

    $('#create-new-request').click(function() {
        PushManager.NewRequestDialog.open_new_request();
    });

    $('.edit-request').click(function() {
        var that = $(this).closest('.request-module');
        var tags = '';
        that.find('ul.tags > li').each(function() {
            if(tags !== '') tags += ' ';
            tags += $(this).text().replace(/^\s+|\s+$/g, '');
        });
        PushManager.NewRequestDialog.open_new_request(
            that.attr('request_title'),
            that.attr('branch'),
            that.attr('repo'),
            that.attr('reviewid'),
            that.find('.request-comments').text().replace(/\n{3,}/g, '\n\n'),
            that.find('.request-description').text(),
            tags,
            that.attr('request'),
            that.attr('user') != PushManager.current_user
        );
    });

    $('.tag-suggestion').click(function() {
        var that = $(this);
        var tagtext = $("#request-form-tags").val();
        var newtag = that.text();
        if(tagtext.indexOf(newtag) == -1) {
            if(tagtext.length > 0) {
                tagtext += " ";
            }
            tagtext += newtag;
            $("#request-form-tags").val(tagtext);
        }
    });

    // Handle bookmarklet requests
    if(PushManager.urlParams['bookmarklet'] == '1') {
        PushManager.NewRequestDialog.open_new_request(
            PushManager.urlParams['title'],
            PushManager.urlParams['branch'],
            PushManager.urlParams['repo'],
            PushManager.urlParams['review'],
            PushManager.urlParams['comments']
        );
    };

    
});
