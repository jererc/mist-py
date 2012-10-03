function initActions() {
    $('.img_button').bind('click', function() {
        var action = $(this).attr('alt');
        var div = $(this).parents('.content_element')[0];

        if (action == 'edit') {
            $(div).find('.element_edit').slideToggle();
            }
        else {
            var form = $(this).parents('form').serializeArray();
            form.push({'name': 'action', 'value': action});

            $.getJSON($SCRIPT_ROOT + '/users/action',
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

$(function() {
    initActions();
    });
