


def save():
    start_time = datetime.now()
    logging_prefix = start_time.strftime("%m/%d/%Y %H:%M:%S") + f" t{os.getpid()}"

    # check params
    params = {}
    if request.values:
        params.update(request.values)

    if 'variant' not in params:
        params.update(request.get_json(force=True, silent=True) or {})

    results = {}

    status = 400 if results.get("error") else 200

    response_json = {}
    response_json.update(params)  # copy input params to output
    response_json.update(results)

    duration = str(datetime.now() - start_time)
    response_json['duration'] = duration

    return Response(json.dumps(response_json), status=status, mimetype='application/json')

