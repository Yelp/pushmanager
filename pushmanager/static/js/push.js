$(function() {
    Settings = window.Settings;
    PushManager = window.PushManager || {};

    $('#push-checklist').dialog({
        autoOpen: false,
        title: 'Push Checklist',
        width: 400,
        height: 600,
        position: 'right'
    });
    PushManager.reload_checklist = function() {
        $('#push-checklist').load('/checklist',
            {
                'id': $('#push-info').attr('push'),
                'pushmaster': (PushManager.current_user == $('#push-info').attr('pushmaster') ? 1 : 0)
            },
            function() {
                if($('#push-checklist .checklist-item').length > 0) {
                    $('#push-checklist').dialog('open');
                }
            });
    };
    PushManager.reload_checklist();
    setInterval("PushManager.reload_checklist()", 30000);
    $('.checklist-item').live('click', function() {
        var that = $(this);
        var ids = that.attr('checklistid').split(',');
        var is_complete = that.attr('checked') ? 1 : 0;
        for (var i=0; i < ids.length; i++) {
            $.ajax({
                'type': 'POST',
                'url': '/checklisttoggle',
                'data': {
                    'id': ids[i],
                    'complete': is_complete
                }
            });
        }
    });
    $('#show-checklist').click(function() {
        $('#push-checklist').dialog('open');
    });

    $('#run-a-command').dialog({
        autoOpen: false,
        modal: true,
        title: 'Run this command:',
        width: 600,
        height: 150,
        resizable: false
    });
    PushManager.run_command_dialog = function(command, callback) {
        PushManager.run_command_dialog_callback = callback;
        $('#command-to-run').text(command);
        $('#run-a-command').dialog('open');
    }
    PushManager.run_command_dialog_callback = function() {};
    $('#command-done').click(function() {
        PushManager.run_command_dialog_callback();
        $('#run-a-command').dialog('close');
    });

    $('#send-message-prompt').dialog({
        autoOpen: false,
        title: 'Send a message:',
        width: 500,
        height: 150
    });
    PushManager.send_message_dialog = function(people) {
        $('#send-message').attr('people', people);
        $('#send-message-contents').val('');
        $('#send-message-prompt').dialog('open');
    }
    $('#send-message').click(function() {
        var that = $(this);
        $.ajax({
            'url': '/msg',
            'type': 'POST',
            'data': {
                'people': that.attr('people').split(', '),
                'message': $('#send-message-contents').val()
            },
            'success': function() {
                $('#send-message-prompt').dialog('close');
            }
        });
    });
    $('.message-people').live('click', function() {
        var contents = $(this).siblings('.item-count').text();

        var people_pat = new RegExp(    // person, person (person, person), person (person), person
            "(?:[a-z]+" +                   // A username, possibly followed by
                "(?:\\s\\(" +               //   a space and (
                    "(?:[a-z]+,?\\s?)+" +   //   and one or more usernames (possibly separated by comma and/or a single space)
                "\\))?" +                   //   followed by a )
            ",?\\s?" +                      // possibly followed by a command and space
            ")+")                           // and more of the same

        var people = (people_pat.exec(contents) || [""])[0];
        PushManager.send_message_dialog(people);
    });
    $('#message-all').live('click', function() {
        var people = PushManager.all_involved_users();
        PushManager.send_message_dialog(people);
    });

    $('#ping-me').live('click', function() {
        var that = $(this);
        if(that.attr('action') == 'set') {
            $.ajax({
                'url': '/pingme',
                'data': {'action': that.attr('action'), 'push': $('#push-info').attr('push')},
                'success': function(data) {
                    that.text("Don't Ping Me");
                    that.attr('action', 'unset');
                }
            });
        } else {
            $.ajax({
                'url': '/pingme',
                'data': {'action': that.attr('action'), 'push': $('#push-info').attr('push')},
                'dataType': 'json',
                'success': function(data) {
                    that.text("Ping Me");
                    that.attr('action', 'set');
                }
            });
        }
    });

    $('#comment-on-request').dialog({
        autoOpen: false,
        title: 'Add a comment:',
        width: 600,
        height: 300
    });
    PushManager.comment_dialog = function(id) {
        $('#submit-request-comment').attr('request', id);
        $('#comment-input-area').val('');
        $('#comment-on-request').dialog('open');
    }
    $('#submit-request-comment').click(function() {
        var that = $(this);
        var comment = $('#comment-input-area').val();
        var id = that.attr('request');
        $.ajax({
            'type': 'POST',
            'url': '/commentrequest',
            'data': {'id': id, 'comment': comment},
            'dataType': 'html',
            'success': function(data) {
                var that = $('.request-module[request="' + id + '"] .request-comments');
                that.html(data);
                PushManager.Request.format_comments_dom(that);
                $('#comment-on-request').dialog('close');
            },
            'error': function() {
                alert("Something went wrong while trying to add a comment on the request.");
            }
        });
    });

    $('#merge-requests').dialog({
        autoOpen: false,
        title: 'Build Deploy Branch',
        width: 500,
        height: 400
    });
    PushManager.merge_dialog = function(removing) {
        if(removing) {
            var requests = $('ul.items-in-push .request-multi-select').not(':checked');
        } else {
            var requests = $('.request-multi-select:checked, ul.items-in-push .request-multi-select');
        }

        var merge_string = "merge-branches";
        var localizations = false;
        requests.each(function() {
            var req = $(this).closest('.request-module');
            if(req.find('.tag-l10n').length > 0) {
                localizations = true;
            }
            if(req.find('.tag-l10n-only').length > 0) {
                localizations = true;
            } else {
                merge_string += ' ' + req.attr('cherry_string');
            }
        });

        if(localizations) {
            merge_string += ' && localizables_push_website.py';
        }

        $('#merge-branches-command').text(merge_string);
        $('#merge-requests').dialog('open');
    };

    $('#add-selected-requests').click(function() {
        PushManager.on_done_merging = PushManager.add_checked_requests;
        PushManager.merge_dialog(false);
    });

    $('#remove-selected-requests').click(function() {
        PushManager.on_done_merging = PushManager.remove_checked_requests;
        PushManager.merge_dialog(true);
    });

    $('#rebuild-deploy-branch').click(function() {
        PushManager.on_done_merging = function(){return;};
        $('.request-multi-select').attr('checked', '');
        PushManager.merge_dialog(false);
    });

    $('#done-merging').click(function() {
        $('#merge-requests').dialog('close');
        PushManager.on_done_merging();
    });

    PushManager.add_checked_requests = function() {
        var requests = $('#requested-items .request-multi-select:checked, #pickme-items .request-multi-select:checked').closest('.request-module').map(function() { return $(this).attr('request'); }).get();
        if(requests.length > 0) {
            $.ajax({
                'url': '/addrequest',
                'data': {'request': requests, 'push': $('#push-info').attr('push')},
                'traditional': true,
                'success': function() {
                    $(requests).each(function() {
                        $('#requested-items .request-module[request=' + this + ']' + ',' +
                          '#pickme-items .request-module[request=' + this + ']'
                            ).parent().detach().appendTo('#added-items').each(function() {;
                                ($.proxy(PushManager.Request.collapse_push_item, this))();
                            });
                    });
                    setTimeout('PushManager.update_status_counts()', 50);
                    $('.request-multi-select').attr('checked', '');
                },
                'error': function() { alert("Adding a request to the push failed."); }
            });
        }
    };

    PushManager.remove_checked_requests = function() {
        var requests = $('.request-multi-select:checked').closest('.request-module').map(function() { return $(this).attr('request'); }).get();
        if(requests.length > 0) {
            $.ajax({
                'url': '/removerequest',
                'data': {'request': requests, 'push': $('#push-info').attr('push')},
                'traditional': true,
                'success': function() {
                    $(requests).each(function() {
                        $('.request-module[request=' + this + ']'
                            ).parent().detach().appendTo('#requested-items').each(function() {;
                                ($.proxy(PushManager.Request.collapse_push_item, this))();
                            });
                    });
                    setTimeout('PushManager.update_status_counts()', 50);
                    $('.request-multi-select').attr('checked', '');
                },
                'error': function() { alert("Removing a request from the push failed."); }
            });
        }
    };

    PushManager.requests_to_names = function(requests) {
        var hash = new Object();
        requests.each(function() {
            if($(this).attr('watchers')) {
                hash[$(this).attr('user') + ' (' + $(this).attr('watchers') + ')'] = true;
            } else {
                hash[$(this).attr('user')] = true;
            }
        });
        var names = new Array();
        for(value in hash) {
            names.push(value);
        }
        return names.join(', ');
    };

    PushManager.section_involved_users = function(section) {
        var requests = $('#' + section + '-items .request-module');
        return PushManager.requests_to_names(requests);
    };

    PushManager.all_involved_users = function() {
        var requests = $('.items-in-push .request-module');
        return PushManager.requests_to_names(requests);
    };

    PushManager.update_status_counts = function() {
        $('.status-header').each(function() {
            var that = $(this);
            var status_items_count = that.next('ul.push-items').children('li').length;
            var status_items_names = PushManager.section_involved_users(that.attr('section'));
            if(status_items_names) {
                that.find('.item-count').text('(' + status_items_count + ' - ' + status_items_names + ')');
            } else {
                that.find('.item-count').text('(' + status_items_count + ')');
            }
        });
        PushManager.reload_checklist();
    };
    PushManager.update_status_counts()

    $('.comment-request').click(function() {
        PushManager.comment_dialog($(this).closest('.request-module').attr('request'));
    });

    $('#edit-push').click(function() {
        $('#push-info-form').show();
    });

    $('#push-cancel').click(function() {
        $('#push-info-form').hide();
    });

    $('#rerun-conflict-check').click(function() {
        $('#confirm-conflict-check').show();
    });

    $('#cancel-conflict-check').click(function() {
        $('#confirm-conflict-check').hide();
    });

    $('#discard-push').click(function() {
        PushManager.run_command_dialog("git push --delete canon " + $('#push-info').attr('branch'), function() {
            // Go ahead and discard it.
            $.post('/discardpush', {'id': $('#push-info').attr('push')}, function() {
                $('#push-survey')[0].maybe_open();
            });
        });
    });

    $('#expand-all-requests').click(function() {
        $('.request-info-extended').show();
        $('.request-item-expander').attr('src', "/static/img/button_hide.gif");
    });

    $('#collapse-all-requests').click(function() {
        $('.request-info-extended').hide();
        $('.request-item-expander').attr('src', "/static/img/button_expand.gif");
    });

    $('#set-stageenv-prompt').dialog({
        autoOpen: false,
        modal: true,
        title: 'Set stage environment:',
        width: 300,
        height: 150
    });
    PushManager.set_stageenv_dialog = function(env) {
        if (env == '') {
            $('#set-stageenv').attr('disabled', 'true');
        }
        $('#set-stageenv-contents').val(env);
        $('#set-stageenv-contents').keyup(function(){
            if ($(this).val() != '') {
                $('#set-stageenv').removeAttr('disabled');
            } else {
                $('#set-stageenv').attr('disabled', 'true');
            }});
        $('#set-stageenv-prompt').dialog('open');
    }

    $('#deploy-to-stage-step0').click(function() {
        PushManager.set_stageenv_dialog($('#push-info').attr('stageenv'))
    });

    $('#set-stageenv').click(function() {
        var that = $(this);
        $.ajax({
            'url': '/editpush',
            'type': 'POST',
            'data': {
                'id': $('#push-info').attr('push'),
                'push-title': $('#push-info').attr('title'),
                'push-branch': $('#push-info').attr('branch'),
                'push-stageenv': $('#set-stageenv-contents').val()
            },
            'success' : function() {
                $('#set-stageenv-prompt').dialog('close');
                $('#push-info').attr('stageenv', $('#set-stageenv-contents').val());
                PushManager.run_command_dialog("deploy-stage --target " + $('#push-info').attr('stageenv') + " -b " + $('#push-info').attr('branch'), function() {
                    // "Cancel" button was not pressed, so mark as deployed to stage
                    $.ajax({
                        'type': 'POST',
                        'url': '/deploypush',
                        'data': {'id': $('#push-info').attr('push')},
                        'success': function() {
                            $("#added-items").children().detach().appendTo('#staged-items');
                            setTimeout('PushManager.update_status_counts()', 50);
                        },
                        'error': function() { alert("Something went wrong when marking the newly added items as staged."); }
                    });
                });
            }
        });
    });

    $('.verify-request').click(function() {
        var that = $(this).closest('.request-module');
        $.ajax({
            'type': 'POST',
            'url': '/verifyrequest',
            'data': {'id': that.attr('request'), 'push': $('#push-info').attr('push')},
            'success': function() {
                that.parent().detach().appendTo('#verified-items');
                setTimeout('PushManager.update_status_counts()', 50);
            },
            'error': function() { alert("Something went wrong when marking the request as verified."); }
        });
    });

    $('.pickme-request').click(function() {
        var that = $(this).closest('.request-module');
        $.ajax({
            'type': 'POST',
            'url': '/pickmerequest',
            'data': {'request': that.attr('request'), 'push': $('#push-info').attr('push')},
            'success': function() {
                that.parent().detach().appendTo('#pickme-items');
                setTimeout('PushManager.update_status_counts()', 50);
            },
            'error': function() { alert("Something went wrong when marking the request as pickme."); }
        });
    });

    $('.unpickme-request').click(function() {
        var that = $(this).closest('.request-module');
        $.ajax({
            'type': 'POST',
            'url': '/unpickmerequest',
            'data': {'request': that.attr('request'), 'push': $('#push-info').attr('push')},
            'success': function() {
                that.parent().detach().appendTo('#requested-items');
                setTimeout('PushManager.update_status_counts()', 50);
            },
            'error': function() { alert("Something went wrong when unmarking the request as pickme."); }
        });
    });

    $('#deploy-to-prod').click(function() {
        var that = $(this);
        if($("#added-items").children().length > 0) {
            alert("There are added requests which have not been staged. You must either stage or remove them.");
            return false;
        } else if($("#staged-items").children().length > 0) {
            alert("There are staged requests which have not been verified. You must either verify or remove them.");
            return false;
        }
        PushManager.run_command_dialog("deploy-prod --source " + $('#push-info').attr('stageenv') + " <deploytag>", function() {
            // "Cancel" button was not pressed, so mark as blessed to prod
            $.ajax({
                'type': 'POST',
                'url': '/blesspush',
                'data': {'id': $('#push-info').attr('push')},
                'success': function() {
                    $("#verified-items").children().detach().appendTo('#blessed-items');
                    setTimeout('PushManager.update_status_counts()', 50);
                },
                'error': function() { alert("Something went wrong when marking the newly added items as blessed."); }
            });
        });
    });

    $('#merge-to-master').click(function() {
        var that = $(this);
        if($("#added-items").children().length > 0 || $("#staged-items").children().length > 0 ||
            $("#verified-items").children().length > 0) {
            alert("There are requests which have not been deployed. You must either remove or deploy them.");
            return false;
        }
        PushManager.run_command_dialog("certify-push " + $('#push-info').attr('branch'), function() {
            // "Cancel" button was not pressed, so mark as merged into master
            $.ajax({
                'type': 'POST',
                'url': '/livepush',
                'data': {'id': $('#push-info').attr('push')},
                'success': function() {
                    $('#push-survey')[0].maybe_open();
                },
                'error': function() { alert("Something went wrong when marking the push live."); }
            });
        });
    });

    $('.add-request').click(function() {
        $('.request-multi-select').attr('checked', '');
        var that = $(this).closest('.request-module');
        that.find('.request-multi-select').attr('checked', 'true');
        PushManager.on_done_merging = PushManager.add_checked_requests;
        PushManager.merge_dialog();
    });

    $('.remove-request').click(function() {
        var that = $(this).closest('.request-module');
        $.ajax({
            'url': '/removerequest',
            'data': {'request': that.attr('request'), 'push': $('#push-info').attr('push')},
            'success': function() {
                that.parent().detach().appendTo('#requested-items');
                setTimeout('PushManager.update_status_counts()', 50);
                $('.request-multi-select').attr('checked', '');
                PushManager.on_done_merging = function() {return;};
                PushManager.merge_dialog();
            },
            'error': function() { alert("Removing a request from the push failed."); }
        });
    });

    setTimeout(function() {
        $('.tag-buildbot').each(function() { PushManager.Request.load_bb_failures(this); });
    }, 1000);

    if ('tests_tag' in Settings) {
        setTimeout(function() {
            $('.tag-'+Settings['tests_tag']['tag']).each(function() { PushManager.Request.load_test_api_tags(this); });
        }, 1000)
    }

    $('#push-survey').dialog({
        autoOpen: false,
        modal: true,
        title: 'Congratulations or condolences, let\'s find out.',
        width: 400,
        height: 120,
        resizable: false
    });
});
