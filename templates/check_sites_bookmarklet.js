(function(){
    Settings = {{ JSSettings_json }};

    var domainName = Settings['check_sites_bookmarklet']['domain_name'];
    var urls = Settings['check_sites_bookmarklet']['urls'];
    // 'substitutions' defines strings that need to be replaced for
    // non-production environments. Example object for this:
    // {'prod_id': 'dev_id'}
	// The example above will replace 'prod_id' with 'dev_id' in the
	// given list of urls.
    var substitutions = Settings['check_sites_bookmarklet']['substitutions'] || {};

    var prod = 'prod';

    var env = window.prompt('Which environment would you like to test? e.g.: prod, stagea, stageb.', prod);

    // If env is false, the user hit 'cancel', and let's abort.
    if (!env) {
        return;
    }

    for (var i=0; i < urls.length; ++i) {
        var url = urls[i];

        // We assume all URLs are encoded against a prod environment.
        // If not, we modify the URL with what we assume to be a testing sub-domain.  e.g.: foo.com -> stage.foo.com
        if (env !== prod) {

            $.each(substitutions, function(prodString, devString) {
                if (url.match(prodString)) {
                    url = url.replace(prodString, devString);
                }
            });

            url = url.replace(domainName, env + '.' + domainName);
        }

        url = 'http://' + url;

        window.open(url, url, 'resizable=yes,menubar=yes,toolbar=yes,scrollbars=yes,status=yes,location=yes');
    }
})();
