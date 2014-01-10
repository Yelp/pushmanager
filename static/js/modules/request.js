$(function() {
    Settings = window.Settings;
    PushManager = window.PushManager || {};
    PushManager.Request = PushManager.Request || {}

    PushManager.Request.format_comments_dom = function(domobj) {
        var link_re = /((?:http:\/\/|https:\/\/)?(?:\w+\.)+(?!py|tmpl|js)[a-z]{2,}(?:\/\S*)*)/ig

        var that = $(domobj);
        var data = that.text();

        // Escape
        data = data.replace(/</g, '&lt;');
        data = data.replace(/>/g, '&gt;');
        data = data.replace(/"/g, '&quot;');

        // Newlines -> Rendered newlines
        data = data.replace(/\n/g, '\n<br>');

        // Bold comment headers
        data = data.replace(/Comment from \w+:/g, function(m) { return '<strong>' + m + '</strong>'; });

        // Linkify
        data = data.replace(link_re, function(match) {
            return '<a target="_blank" href="' + match + '">' + match + '</a>';
        });

        that.html(data);
    };

    // Format initial comments
    $('.request-comments').each(function() { PushManager.Request.format_comments_dom(this); });
    $('.request-description').each(function() { PushManager.Request.format_comments_dom(this); });


    PushManager.Request.expand_push_item = function() {
        var that = $(this);
        var req = that.closest('.request-module');
        req.find('.request-info-extended').toggle();
        var button = req.find('.request-item-expander');
        if(button.attr('src') == "/static/img/button_hide.gif") {
            button.attr('src', "/static/img/button_expand.gif");
        } else {
            button.attr('src', "/static/img/button_hide.gif");
        }
    };

    PushManager.Request.collapse_push_item = function() {
        var that = $(this);
        var req = that.find('.request-module');
        req.find('.request-info-extended').hide();
        var button = req.find('.request-item-expander');
        button.attr('src', "/static/img/button_expand.gif");
    };

    // Bind expander to both title and expand icon
    $('.request-item-expander, .request-item-title').live('click', PushManager.Request.expand_push_item);
    $('.request-item-expander[expand=yes]').each(PushManager.Request.expand_push_item);


    PushManager.Request.delay_request = function() {
        var that = $(this).closest('.request-module');
        var requestid = that.attr('request');
        $.ajax({
            'type': 'POST',
            'url': '/delayrequest',
            'data': {'id': requestid},
            'success': function() { window.location.reload(); },
            'error': function() { alert('Something went wrong while trying to delay the request.'); }
        });
    };

    PushManager.Request.pushmaster_delay_request = function() {
        var that = $(this).closest('.request-module');
        var requestid = that.attr('request');
        $.ajax({
            'type': 'POST',
            'url': '/delayrequest',
            'data': {'id': requestid},
            'success': function() { that.parent("li").remove(); },
            'error': function() { alert('Something went wrong while trying to delay the request.'); }
        });
    };

    PushManager.Request.undelay_request = function() {
        var that = $(this).closest('.request-module');
        var requestid = that.attr('request');
        $.ajax({
            'type': 'POST',
            'url': '/undelayrequest',
            'data': {'id': requestid},
            'success': function() { window.location.reload(); },
            'error': function() { alert('Something went wrong while trying to un-delay the request.'); }
        });
    };

    PushManager.Request.discard_request = function() {
        var that = $(this).closest('.request-module');
        var requestid = that.attr('request');
        if(confirm("Are you sure you want to discard this request?")) {
            $.ajax({
                'type': 'POST',
                'url': '/discardrequest',
                'data': {'id': requestid},
                'success': function() { window.location.reload(); },
                'error': function() { alert('Something went wrong while trying to discard the request.'); }
            });
        }
    };

    // Bind various buttons
    $('.delay-request').live('click', PushManager.Request.delay_request);
    $('.pushmaster-delay-request').live('click', PushManager.Request.pushmaster_delay_request);
    $('.undelay-request').live('click', PushManager.Request.undelay_request);
    $('.discard-request').live('click', PushManager.Request.discard_request);

    PushManager.Request.load_bb_failures = function(domobj) {
        var dataurl = "https://" + Settings['buildbot']['servername'] + "/rev/%REVISION%";
        var that = $(domobj);
        if(that.hasClass('bb-data-loaded')) {
            return;
        }
        var req = that.closest('.request-module');

        var revision = req.attr('revision');
        $.ajax({
            'url': dataurl.replace('%REVISION%', revision),
            'data': {'format': 'json'},
            'dataType': 'json',
            'success': function(data) {
                if(!data || data.error) {
                    that.find('a').first().append(' (<span style="color: #f08;">NOT FOUND</span> - rev changed?)');
                } else {
                    var a = that.find('a').first();
                    a.append(' (');
                    a.append('' + data['total_fails'] + ' fails');
                    a.append(',  ' + data['total_flakes'] + ' flakes');
                    if(data['total_unfinished']) {
                        a.append(', ' + data['total_unfinished'] + ' unfinished');  
                    }
                    if(data['missing_builders']) {
                        a.append(', <span style="color: #f08;">' + data['missing_builders'] + ' missing</span>');   
                    }
                    if(data['unfinished_builders']) {
                        a.append(', <span style="color: #f08;">' + data['unfinished_builders'] + ' builders not finished</span>');
                    }
                    a.append(')');
                }
                that.addClass('bb-data-loaded');
            }
        });
    };
});
