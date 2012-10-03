function initMoreAction() {
    $('.img_button').bind('click', function() {
        var action = $(this).attr('alt');
        var div = $(this).parents('.content_element')[0];

        if (action == 'more') {
            $(div).find('.element_info').slideToggle();
            }

        return false;
        });
    };

function updateStatus() {
    $('.content_element').each( function(result) {
        var title = $(this).find('.title');

        $.getJSON($SCRIPT_ROOT + '/hosts/status',
            {id: $(this).find('input[name="id"]').val()},
            function(data) {
                if (data.result) {
                    title.css('color', 'green');
                    }
                else {
                    title.css('color', 'red');
                    }

                });
        });
    };

$(function() {
    initMoreAction();
    updateStatus();
    var status_interval = window.setInterval(updateStatus, 5000);
    });
