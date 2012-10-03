function initActions() {
    $('.img_button').bind('click', function() {
        var div = $(this).parents('.content_element')[0];
        var action = $(this).attr('alt');

        if (action == 'edit') {
            $(div).find('.element_edit').slideToggle();
            }
        else if (action == 'more') {
            $(div).find('.element_more').slideToggle();
            }
        else {
            var form = $(this).parents('form').serializeArray();
            form.push({'name': 'action', 'value': action});

            $.getJSON($SCRIPT_ROOT + '/syncs/action',
                form,
                function(data) {
                    if (data.result == 'remove') {
                        $(div).fadeOut();
                        }
                    else if (data.result) {
                        location.reload();
                        }
                    });
            }

        return false;
        });
    };

function updateStatus() {
    if (has_focus) {
        $('.content_element').each( function(result) {
            var title = $(this).find('.title');

            $.getJSON($SCRIPT_ROOT + '/syncs/status',
                {id: $(this).find('input[name="id"]').val()},
                function(data) {
                    if (data.result == 'processing') {
                        title.css('color', 'green');
                        }
                    else if (data.result == 'failed') {
                        title.css('color', 'red');
                        }
                    else {
                        title.css('color', '#bbb');
                        }
                    });
            });
        }
    };

$(function() {
    initActions();
    updateStatus();
    var status_interval = window.setInterval(updateStatus, 5000);
    });
