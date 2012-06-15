$(function() {
    $('.button').bind('click', function() {
        var action = this.value;
        var div = $(this).parents('.content_element')[0];
        var form = $(this).parents('form').serializeArray();
        // Add the submit button value
        form.push({'name': 'action', 'value': action});

        $.getJSON($SCRIPT_ROOT + '/syncs/action',
            form,
            function(data) {
                location.reload();
                });
        return false;
        });
    });
