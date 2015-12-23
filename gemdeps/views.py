import json
import os
import time
import glob

from flask import Markup, render_template, request, redirect

from gemdeps import app


def list_apps():
    SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
    list_of_json = glob.glob(os.path.join(
        SITE_ROOT, 'static', '*_debian_status.json'))
    apps = {}
    for jsonfile in list_of_json:
        pos = len(jsonfile) - jsonfile[::-1].index('/')
        appfilename = jsonfile[pos:]
        appname = appfilename[:appfilename.index('_')]
        apps[appname] = jsonfile
    return apps


@app.route('/', methods=['GET', 'POST'])
def index():
    gemnames = []
    available_apps = list_apps()
    if not available_apps:
        return render_template('no_files.html')
    for app in available_apps:
        filepath = available_apps[app]
        inputfile = open(filepath)
        filecontent = inputfile.read()
        inputfile.close()
        deps = json.loads(filecontent)
        gemnames += [str(x['name']) for x in deps]
    gemnames = list(set(gemnames))
    gemnames.sort()
    gemnames = Markup(gemnames)
    return render_template('index.html', gemnames=gemnames,
                           apps=available_apps)


@app.route('/info', methods=['GET', 'POST'])
def info():
    apps = request.args.getlist('appname')
    print "Apps: ", apps
    gemname = request.args.get('gemname')
    completedeplist = {}
    gemnames = []
    available_apps = list_apps()
    if not available_apps:
        return render_template('no_files.html')
    for app in available_apps:
        filepath = available_apps[app]
        inputfile = open(filepath)
        filecontent = inputfile.read()
        inputfile.close()
        deps = json.loads(filecontent)
        completedeplist[app] = deps
        gemnames += [str(x['name']) for x in deps]
    gemnames = list(set(gemnames))
    gemnames.sort()
    gemnames = Markup(gemnames)
    if not apps:
        if not gemname:
            flag = 1
            return render_template('info.html', gemnames=gemnames,
                                   apps=available_apps, flag=flag)
        else:
            apps = available_apps
    gems = {}
    flag = 0
    for app in apps:
        if app in available_apps:
            gem = [x for x in completedeplist[app] if x['name'] == gemname]
            if gem:
                flag = 1
            gems[app] = gem
    return render_template('info.html',
                           gemnames=gemnames,
                           gemname=gemname,
                           gemlist=gems,
                           flag=flag,
                           apps=available_apps)


@app.route('/status/<appname>')
def status(appname):
    apps = list_apps()
    if not apps or appname not in apps:
        return render_template('no_files.html')
    ignore_list = ['mini_portile2', 'newrelic_rpm', 'newrelic-grape',
                   'rb-fsevent', 'eco', 'eco-source']
    SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
    appfilename = appname + "_debian_status.json"
    filepath = os.path.join(SITE_ROOT, "static", appfilename)
    inputfile = open(filepath)
    filecontent = inputfile.read()
    inputfile.close()
    updated_time = time.strftime(
        "%d/%m/%Y %H:%M:%S %Z", time.gmtime(os.path.getmtime(filepath)))
    deps = json.loads(filecontent)
    packaged_count = 0
    unpackaged_count = 0
    itp_count = 0
    total = 0
    mismatch = 0
    final_list = []
    for i in deps:
        if i['name'] in ignore_list:
            continue
        else:
            final_list.append(i)
            if i['status'] == 'Packaged' or i['status'] == 'NEW':
                packaged_count += 1
            elif i['status'] == 'ITP':
                itp_count += 1
            else:
                unpackaged_count += 1
            if i['satisfied'] == False:
                mismatch += 1
    total = len(final_list)
    print total
    percent_complete = (packaged_count * 100) / total
    return render_template('status.html',
                           appname=appname.title(),
                           deps=final_list,
                           packaged_count=packaged_count,
                           unpackaged_count=unpackaged_count,
                           itp_count=itp_count,
                           mismatch_count=mismatch,
                           total=total,
                           percent_complete=percent_complete,
                           updated_time=updated_time,
                           apps=apps
                           )


@app.route('/about')
def about():
    apps = list_apps()
    return render_template('about.html', apps=apps)


def compare_lists(first_list, second_list):
    first_list_names = [x['name'] for x in first_list]
    result = []
    for item in second_list:
        if item['name'] in first_list_names:
            result.append(item)
    return result


@app.route('/compare')
def compare():
    available_apps = list_apps()
    apps = request.args.getlist('appname')
    if len(apps) < 2:
        if len(apps) == 1:
            return redirect("/status/%s" % apps[0])
        else:
            return redirect("/")
    result = []
    app_dep_list = []
    for appname in apps:
        print appname
        if appname not in available_apps:
            apps.remove(appname)
            continue
        else:
            SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
            appfilename = appname + "_debian_status.json"
            filepath = os.path.join(SITE_ROOT, "static", appfilename)
            inputfile = open(filepath)
            filecontent = inputfile.read()
            inputfile.close()
            deps = json.loads(filecontent)
            app_dep_list.append(deps)
    first_list = app_dep_list[0]
    second_list = app_dep_list[1]
    counter = 1
    while counter < len(app_dep_list):
        counter = counter + 1
        result = compare_lists(first_list, second_list)
        first_list = result
        if counter < len(app_dep_list):
            second_list = app_dep_list[counter]
    final = {}
    for i in result:
        current = {}
        counter = 0
        while counter < len(app_dep_list):
            appname = apps[counter]
            for item in app_dep_list[counter]:
                if item['name'] == i['name']:
                    current[appname] = item
            counter = counter+1
        final[i['name']] = current
    color = {}
    for gem in final:
        keys = final[gem].keys()
        current_color = final[gem][keys[0]]['color']
        if current_color != 'green':
            color[gem] = 'red'
        else:
            for app in final[gem]:
                if current_color != final[gem][app]['color']:
                    color[gem] = 'violet'
                    break
                color[gem] = current_color
    return render_template('compare.html',
                           apps=available_apps,
                           selected_apps=apps,
                           final=final,
                           color=color
                           )
