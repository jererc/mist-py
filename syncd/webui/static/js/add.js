function initAddAction() {
    $('.button').bind('click', function() {
        var form = $(this).parents('form').serializeArray();

        $.getJSON($SCRIPT_ROOT + '/add/action',
            form,
            function(data) {
                if (data.result) {
                    location.reload();
                    }
                });

        return false;
        });
    };

$(function() {
    initAddAction();
    });
