$(function() {
    $('.button').bind('click', function() {
        var form = $(this).parents('form').serializeArray();

        $.getJSON($SCRIPT_ROOT + '/add/action',
            form,
            function(data) {
                location.reload();
                });
        return false;
        });
    });
