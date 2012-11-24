function initActions() {
    $('.img_button[alt="edit"]').bind('click', function() {
        var div = $(this).parents('.content_element')[0];
        $(div).find('.element_edit').slideToggle('fast');
        $(div).find('.save_action').fadeToggle('fast');
        return false;
        });

    $('.img_button[alt="add"]').bind('click', function() {
        var div = $(this).parents('.content_new')[0];
        $.getJSON($SCRIPT_ROOT + '/users/add',
            $(div).find('form').serializeArray(),
            function(data) {
                if (data.result) {
                    location.reload();
                    }
                });
        return false;
        });

    $('.img_button[alt="update"]').bind('click', function() {
        var div = $(this).parents('.content_element')[0];
        $.getJSON($SCRIPT_ROOT + '/users/update',
            $(this).parents('form').serializeArray(),
            function(data) {
                if (data.result) {
                    location.reload();
                    }
                });
        return false;
        });

    $('.img_button[alt="remove"]').bind('click', function() {
        var div = $(this).parents('.content_element')[0];
        $.getJSON($SCRIPT_ROOT + '/users/remove',
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
