CREATE OR REPLACE FUNCTION public.test_plpython(
	)
    RETURNS text
    LANGUAGE 'plpython3u'
    COST 100
    VOLATILE PARALLEL UNSAFE
AS $BODY$
    return "PL/Python is working!"
$BODY$;
