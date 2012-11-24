function initActions() {
    $('.content_element').mouseover(function() {
        $(this).addClass('element_highlight');
        $(this).find('.element_details').slideDown('fast');
        });
    $('.content_element').mouseleave(function() {
        $(this).removeClass('element_highlight');
        $(this).find('.element_details').slideUp('fast');
        });

    $('.img_button[alt="more"]').bind('click', function() {
        var div = $(this).parents('.content_element')[0];
        $(div).find('.element_info').slideToggle('fast');
        return false;
        });
    };

function updateStatus() {
    $('.content_element').each(function(result) {
        var status = $(this).find('.host_status');
        var title = $(this).find('.title');

        $.getJSON($SCRIPT_ROOT + '/hosts/status',
            {id: $(this).find('input[name="id"]').val()},
            function(data) {
                if (data.result) {
                    status.addClass('host_up');
                    status.removeClass('host_down');
                    status.html('up');
                    }
                else {
                    status.addClass('host_down');
                    status.removeClass('host_up');
                    status.html('down');
                    }
                });
        });
    };

$(function() {
    initActions();
    updateStatus();
    var status_interval = window.setInterval(updateStatus, 5000);
    });
