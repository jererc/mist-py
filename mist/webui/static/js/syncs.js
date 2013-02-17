function initActions() {
    $('.img-button[alt="edit"]').click(function() {
        var div = $(this).parents('.content-element')[0];
        $(div).find('.element-edit').slideToggle('fast');
        $(div).find('.save-action').fadeToggle('fast');
        return false;
    });

    $('.img-button[alt="add"]').click(function() {
        var div = $(this).parents('.content-new')[0];
        var form = $(div).find('form');
        $.getJSON($SCRIPT_ROOT + '/syncs/add',
            form.serializeArray(),
            function(data) {
                if (data.result) {
                    location.reload();
                }
            });
        return false;
    });

    $('.img-button[alt="update"]').click(function() {
        var div = $(this).parents('.content-element')[0];
        $.getJSON($SCRIPT_ROOT + '/syncs/update',
            $(this).parents('form').serializeArray(),
            function(data) {
                if (data.result) {
                    location.reload();
                }
            });
        return false;
    });

    $('.img-button[alt="reset"]').click(function() {
        var div = $(this).parents('.content-element')[0];
        $.getJSON($SCRIPT_ROOT + '/syncs/reset',
            $(this).parents('form').serializeArray(),
            function(data) {
                if (data.result) {
                    location.reload();
                }
            });
        return false;
    });

    $('.img-button[alt="remove"]').click(function() {
        var div = $(this).parents('.content-element')[0];
        $.getJSON($SCRIPT_ROOT + '/syncs/remove',
            $(this).parents('form').serializeArray(),
            function(data) {
                if (data.result) {
                    $(div).fadeOut('fast');
                }
            });
        return false;
    });
};

$(function() {
    initActions();
});
