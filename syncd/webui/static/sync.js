$(function() {
    $('.button').bind('click', function() {
        var action = this.value;
        var div = $(this).parents('.content_element')[0];
        var form = $(this).parents('form').serializeArray();
        // Add the submit button value
        form.push({'name': 'action', 'value': action});

        $.getJSON($SCRIPT_ROOT + '/action',
            form,
            function(data) {
                location.reload();
                });
        return false;
        });
    });

$(function() {
    $('.img_button').bind('click', function() {
        var action = $(this).attr('alt');
        var div = $(this).parents('.content_element')[0];
        var form = $(this).parents('form').serializeArray();
        // Add the submit button value
        form.push({'name': 'action', 'value': action});

        if (action == 'edit') {
            $(div).find('.element_edit').fadeToggle();
            }
        else {
            $.getJSON($SCRIPT_ROOT + '/action',
                form,
                function(data) {
                    if (data.result == 'remove') {
                        $(div).fadeOut();
                        }
                    else {
                        location.reload();
                        }
                    });
            }
        return false;
        });
    });
