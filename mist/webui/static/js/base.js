var showDelays = {};


function toggleElement(id, element, direction, delay) {
    clearTimeout(showDelays[id]);
    if (!element) {
        return false;
    }
    showDelays[id] = setTimeout(function() {
        if (direction == 'up') {
            element.slideUp(300);
        } else {
            element.slideDown(100);
        }
    }, delay);
};

function initBaseActions() {
    $('.content-new-trigger, .content-new').mouseenter(function() {
        toggleElement('new', $('.content-new'), 'down', 500);
    });
    $('.content-new-trigger').mouseleave(function() {
        toggleElement('new');
    });
    $('.content-new').mouseleave(function() {
        toggleElement('new', $(this), 'up', 600);
    });

    $('.content-element').mouseenter(function() {
        $(this).addClass('element-highlight');
        toggleElement($(this).attr('data-id'),
                $(this).find('.element-info'), 'down', 600);
    });
    $('.content-element').mouseleave(function() {
        $(this).removeClass('element-highlight');
        toggleElement($(this).attr('data-id'),
                $(this).find('.element-info'), 'up', 2000);
    });

    if (isMobile) {
        $('.element-actions').each(function() {
            $(this).show();
        });
    } else {
        $('.content-element').mouseenter(function() {
            $(this).find('.element-actions').show();
        });
        $('.content-element').mouseleave(function() {
            $(this).find('.element-actions').hide();
        });
    }

};

$(function() {
    initBaseActions();
});
