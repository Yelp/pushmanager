(function(){
	Settings = window.Settings;
    var urls = Settings['verify_urls'];

    var prod = 'prod';

    var env = window.prompt('Which environment would you like to test? e.g.: prod, stagea, stageb.', prod);

    for (var i=0; i < urls.length; ++i) {
        var url = urls[i];
        if (env !== prod) {
            url = env + url;
        }
		url = 'http://' + url;
        window.open(url, url, 'resizable=yes,scrollbars=yes,status=yes');
    }
})();
