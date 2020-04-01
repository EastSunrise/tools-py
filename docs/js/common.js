$(function () {
    $("a").each(function () {
        if ($(this).attr('href').startsWith('http')) {
            $(this).attr('target', '_blank');
        }
    });
});