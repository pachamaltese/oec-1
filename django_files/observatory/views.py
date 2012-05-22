# -*- coding: utf-8 -*-
# Django
from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404, HttpResponsePermanentRedirect, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.template import RequestContext
from django.core.urlresolvers import resolve
# General
import json
# Project specific
from django.utils.translation import gettext as _
# App specific
from observatory.models import *

def new_ps(request):
	ps_nodes = Sitc4.objects.get_all("en")
	return render_to_response("new_ps.html", {"ps_nodes":json.dumps(ps_nodes, indent=2)},context_instance=RequestContext(request))

def home(request):
	try:
		ip = request.META["HTTP_X_FORWARDED_FOR"]
	except KeyError:
		ip = request.META["REMOTE_ADDR"]
	return render_to_response("home.html", context_instance=RequestContext(request))

def about(request):
	return render_to_response("about/index.html", context_instance=RequestContext(request))
def team(request):
	return render_to_response("about/team.html", context_instance=RequestContext(request))
def permissions(request):
	return render_to_response("about/permissions.html", context_instance=RequestContext(request))
def about_data(request, data_type):
	lang = request.session['django_language'] if 'django_language' in request.session else "en"
	lang = request.GET.get("lang", lang)
	if data_type == "sitc4":
		items = [[getattr(x, "name_%s"% (lang,)), x.code] for x in Sitc4.objects.filter(community__isnull=False)]
		headers = ["Name", "SITC4 Code"]
		title = "SITC4 product names and codes"
	elif data_type == "hs4":
		items = [[x.name, x.code] for x in Hs4.objects.filter(community__isnull=False)]
		headers = ["Name", "HS4 Code"]
		title = "HS4 (harmonized system) product names and codes"
	elif data_type == "country":
		items = [[getattr(x, "name_%s"% (lang,)), x.name_3char] for x in Country.objects.filter(name_3char__isnull=False, name_2char__isnull=False, region__isnull=False)]
		headers = ["Name", "Alpha 3 Abbreviation"]
		title = "Country names and abbreviations"
	items.sort()
	return render_to_response("about/data.html",
		{"items":items, "headers":headers, "title": title},
		context_instance=RequestContext(request))

def api(request):
	return render_to_response("api/index.html", context_instance=RequestContext(request))

def api_apps(request):
	return render_to_response("api/apps.html", context_instance=RequestContext(request))

def api_data(request):
	return render_to_response("api/data.html", context_instance=RequestContext(request))

def book(request):
	return render_to_response("book/index.html", context_instance=RequestContext(request))

def set_language(request, lang):
	next = request.REQUEST.get('next', None)
	if not next:
		next = request.META.get('HTTP_REFERER', None)
	if not next:
		next = '/'
	response = HttpResponseRedirect(next)
	# if request.method == 'GET':
	# 	lang_code = request.GET.get('language', None)
	lang_code = lang
	if lang_code:
		if hasattr(request, 'session'):
			request.session['django_language'] = lang_code
		else:
			response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang_code)
			translation.activate(lang_code)
	return response

def set_product_classification(request, prod_class):
	next = request.REQUEST.get('next', None)
	if not next:
		next = request.META.get('HTTP_REFERER', None)
	if not next:
		next = '/'
	response = HttpResponseRedirect(next)
	if prod_class:
		if hasattr(request, 'session'):
			request.session['product_classification'] = prod_class
	return response

def download(request):
	try:
		import cairo, rsvg, xml.dom.minidom
	except:
		pass
	import csv
	content = request.POST.get("content")
	title = request.POST.get("title")
	format = request.POST.get("format")
	
	if format == "svg" or format == "pdf" or format == "png":
		svg = rsvg.Handle(data=content.encode("utf-8"))
		x = width = svg.props.width
		y = height = svg.props.height
	
	if format == "svg":
		response = HttpResponse(content.encode("utf-8"), mimetype="application/octet-stream")
			
	elif format == "pdf":	
		response = HttpResponse(mimetype='application/pdf')
		surf = cairo.PDFSurface(response, x, y)
		cr = cairo.Context(surf)
		svg.render_cairo(cr)
		surf.finish()
	
	elif format == "png":	
		response = HttpResponse(mimetype='image/png')
		surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, x, y)
		cr = cairo.Context(surf)
		svg.render_cairo(cr)
		surf.write_to_png(response)
	
	else:
		response = HttpResponse(mimetype="text/csv;charset=UTF-8")
		csv_writer = csv.writer(response, delimiter=',', quotechar='"')#, quoting=csv.QUOTE_MINIMAL)
		item_list = json.loads(content,encoding='utf-8')
    # raise Exception(content)
    # raise Exception(aa)
		for item in item_list:
			csv_writer.writerow([i.encode("utf-8") for i in item])
	
	# Need to change with actual title
	response["Content-Disposition"]= "attachment; filename=%s.%s" % (title, format)
	
	return response

def app(request, app_name, trade_flow, filter, year):
	# Get URL query parameters
	format = request.GET.get("format", False)
	lang = request.GET.get("lang", False)
	crawler = request.GET.get("_escaped_fragment_", False)
	
	country1, country2, product = None, None, None
	country1_list, country2_list, product_list, year1_list, year2_list, year_interval_list, year_interval = None, None, None, None, None, None, None
	
	trade_flow_list = ["export", "import", "net_export", "net_import"]
	
	year1_list = range(1962, 2010, 1)
	if "." in year:
		y = [int(x) for x in year.split(".")]
		year = range(y[0], y[1]+1, y[2])
		year2_list = year1_list
		year_interval_list = range(1, 11)
		year_interval = year[1] - year[0]
	else:
		year = int(year)
	
	json_response = {
		"year": year,
		"app": app_name
	}
	
	# Bilateral
	if "." in filter:
		bilateral_filters = filter.split(".")
		
		# Country x Product
		if len(bilateral_filters[1]) > 3:
			country1 = Country.objects.get(name_3char=bilateral_filters[0])
			product = Sitc4.objects.get(code=bilateral_filters[1])
			
			# Lists used for control pane
			country1_list = Country.objects.get_all(lang)
			product_list = Sitc4.objects.get_all(lang)
			trade_flow_list = ["export", "import"]
			
			article = "to" if trade_flow == "export" else "from"
			title = "Where does %s %s %s %s?" % (country1.name, trade_flow, product.name_en, article)
			
			# cspy means country1 / countr2 / show / year
			if crawler == "" or format == "json":
				json_response["data"] = Sitc4_ccpy.objects.cspy(country1, product, trade_flow)
				json_response["attr_data"] = Country.objects.get_all(lang)
				json_response["title"] = title
			
		# Country x Country
		else:
			country1 = Country.objects.get(name_3char=bilateral_filters[0])
			country2 = Country.objects.get(name_3char=bilateral_filters[1])

			# Lists used for control pane
			country1_list = Country.objects.get_all(lang)
			country2_list = country1_list
			trade_flow_list = ["export", "import"]
			
			article = "to" if trade_flow == "export" else "from"
			title = "What does %s %s %s %s?" % (country1.name, trade_flow, article, country2.name)
			
			# ccsy means country1 / countr2 / show / year
			if crawler == "" or format == "json":
				json_response["data"] = Sitc4_ccpy.objects.ccsy(country1, country2, trade_flow)
				json_response["attr_data"] = Sitc4.objects.get_all(lang)
				json_response["title"] = title
	
	# Product
	elif len(filter) > 3:
		product = Sitc4.objects.get(code=filter)
		product_list = Sitc4.objects.get_all(lang)
				
		title = "Who %ss %s?" % (trade_flow.replace("_", " "), product.name_en)
		
		# sapy means show / all / product / year
		if crawler == "" or format == "json":
			json_response["data"] = Sitc4_cpy.objects.sapy(product, trade_flow)
			json_response["attr_data"] = Country.objects.get_all(lang)
			json_response["title"] = title
	
	# Country
	else:
		country1 = Country.objects.get(name_3char=filter)
		country1_list = Country.objects.get_all(lang)
		
		title = "What does %s %s?" % (country1.name, trade_flow.replace("_", " "))
		
		# casy means country1 / all / show / year
		if crawler == "" or format == "json":
			json_response["data"] = Sitc4_cpy.objects.casy(country1, trade_flow)
			json_response["attr_data"] = Sitc4.objects.get_all(lang)
			json_response["title"] = title
	
	# Send data as JSON to browser via AJAX
	if format == "json":
		return HttpResponse(json.dumps(json_response))
	
	# Return page without visualization data
	return render_to_response("app/index.html", {
		"title": title,
		"trade_flow": trade_flow,
		"country1": country1,
		"country2": country2,
		"product": product,
		"year": year,
		"trade_flow_list": trade_flow_list,
		"country1_list": country1_list,
		"country2_list": country2_list,
		"product_list": product_list,
		"year1_list": year1_list,
		"year2_list": year2_list,
		"year_interval": year_interval,
		"year_interval_list": year_interval_list}, context_instance=RequestContext(request))

def app_redirect(request, app_name, trade_flow, filter, year):
	# Corrent for old spelling of tree map as one word
	if app_name == "treemap":
		app_name = "tree_map"
	
	# Bilateral
	if "." in filter:
		bilateral_filters = filter.split(".")
		
		# Country x Product
		if len(bilateral_filters[1]) > 3:
			country1, country2, product = bilateral_filters[0], "show", bilateral_filters[1]
			
		# Country x Country
		else:
			country1, country2, product = bilateral_filters[0], bilateral_filters[1], "show"
	
	# Product
	elif len(filter) > 3:
		country1, country2, product = "show", "all", filter
	
	# Country
	else:
		country1, country2, product = filter, "all", "show"
	# raise Exception("/explore/%s/%s/%s/%s/%s/%s/" % (app_name, trade_flow, country1, country2, product, year))
	return HttpResponsePermanentRedirect("/explore/%s/%s/%s/%s/%s/%s/" % (app_name, trade_flow, country1, country2, product, year))

def explore(request, app_name, trade_flow, country1, country2, product, year="2009"):
	# raise Exception(country1, country2, product, year)
	# Get URL query parameters
	crawler = request.GET.get("_escaped_fragment_", False)
	options = request.GET.copy()
	# set language (if session data available use that as default)
	lang = request.session['django_language'] if 'django_language' in request.session else "en"
	lang = request.GET.get("lang", lang)
	options["lang"] = lang
	# set product classification (if session data available use that as default)
	prod_class = request.session['product_classification'] if 'product_classification' in request.session else "hs4"
	prod_class = request.GET.get("product_classification", prod_class)
	options["product_classification"] = prod_class
	options = options.urlencode()
	
	# get distince years from db, different for diff product classifications
	years_available = list(Sitc4_cpy.objects.values_list("year", flat=True).distinct()) if prod_class == "sitc4" else list(Hs4_cpy.objects.values_list("year", flat=True).distinct())
	years_available.sort()
	
	country1_list, country2_list, product_list, year1_list, year2_list, year_interval_list, year_interval = None, None, None, None, None, None, None
	alert = None
	title = None
	data_as_text = {}
	# What is actually being shown on the page
	item_type = "products"
	
	trade_flow_list = [("export", _("Export")), ("import", _("Import")), ("net_export", _("Net Export")), ("net_import", _("Net Import"))]
	if app_name == "product_space":
		trade_flow_list = [trade_flow_list[0]]
	
	year1_list = range(years_available[0], years_available[len(years_available)-1]+1, 1)
	
	if app_name == "stacked" and year == "2009":
		year = "1969.2009.10"
	if "." in year:
		y = [int(x) for x in year.split(".")]
		# year = range(y[0], y[1]+1, y[2])
		year_start = y[0]
		year_end = y[1]
		year_interval = y[2]
		year2_list = year1_list
		year_interval_list = range(1, 11)
		# year_interval = year[1] - year[0]
	else:
		year_start, year_end, year_interval = None, None, None
		year = int(year)
		if year > years_available[len(years_available)-1]:
			year = years_available[len(years_available)-1]
		elif year < years_available[0]:
			year = years_available[0]
	
	api_uri = "/api/%s/%s/%s/%s/%s/?%s" % (trade_flow, country1, country2, product, year, options)
	
	if crawler == "":
		view, args, kwargs = resolve("/api/%s/%s/%s/%s/%s/" % (trade_flow, country1, country2, product, year))
		kwargs['request'] = request
		view_response = view(*args, **kwargs)
		data_as_text["data"] = view_response[0]
		data_as_text["total_value"] = view_response[1]
		data_as_text["columns"] = view_response[2]
	
	app_type = get_app_type(country1, country2, product, year)
	
	# first check for errors
	# check whether country can be found in database
	countries = [None, None]
	country_lists = [None, None]
	for i, country in enumerate([country1, country2]):
		if country != "show" and country != "all":
			try:
				countries[i] = Country.objects.get(name_3char=country)
				country_lists[i] = Country.objects.get_all(lang)
			except Country.DoesNotExist:
				alert = {"title": "Country could not be found",
					"text": "There was no country with the 3 letter abbreviateion <strong>%s</strong>. Please double check the <a href='/about/data/country/'>list of countries</a>."%(country)}
	if product != "show" and product != "all":
		if prod_class == "sitc4":
			product_list = Sitc4.objects.get_all(lang)
			try:
				product = Sitc4.objects.get(code=product)
			except Sitc4.DoesNotExist:
				alert = {"title": "Product could not be found",
					"text": "There was no product with the 4 digit code <strong>%s</strong>. Please double check the <a href='/about/data/sitc4/'>list of SITC4 products</a>."%(product)}
		if prod_class == "hs4":
			product_list = Hs4.objects.get_all(lang)
			try:
				product = Hs4.objects.get(code=product)
			except Hs4.DoesNotExist:
				alert = {"title": "Product could not be found",
					"text": "There was no product with the 4 digit code <strong>%s</strong>. Please double check the <a href='/about/data/hs4/'>list of HS4 products</a>."%(product)}
	
	if not alert:
		if app_type == "casy":
			title = "What does %s %s?" % (countries[0].name, trade_flow.replace("_", " "))
	
		# Country but showing other country trade partners
		elif app_type == "csay":
			item_type = "countries"
			article = "to" if trade_flow == "export" else "from"
			title = "Where does %s %s %s?" % (countries[0].name, trade_flow.replace("_", " "), article)
	
		# Product
		elif app_type == "sapy":
			item_type = "countries"
			title = "Who %ss %s?" % (trade_flow.replace("_", " "), product.name_en)
	
		# Bilateral Country x Country
		elif app_type == "ccsy":
			# trade_flow_list = ["export", "import"]
			if _("net_export") in trade_flow_list: del trade_flow_list[trade_flow_list.index(_("net_export"))]
			if _("net_import") in trade_flow_list: del trade_flow_list[trade_flow_list.index(_("net_import"))]
		
			article = "to" if trade_flow == "export" else "from"
			title = "What does %s %s %s %s?" % (countries[0].name, trade_flow, article, countries[1].name)
	
		# Bilateral Country / Show / Product / Year
		elif app_type == "cspy":
			if "net_export" in trade_flow_list: del trade_flow_list[trade_flow_list.index("net_export")]
			if "net_import" in trade_flow_list: del trade_flow_list[trade_flow_list.index("net_import")]
		
			item_type = "countries"
		
			article = "to" if trade_flow == "export" else "from"
			title = "Where does %s %s %s %s?" % (countries[0].name, trade_flow, product.name_en, article)
	
	# Return page without visualization data
	return render_to_response("explore/index.html", {
		"alert": alert,
		"product_classification": prod_class,
		"years_available": years_available,
		"data_as_text": data_as_text,
		"app_name": app_name,
		"title": title,
		"trade_flow": trade_flow,
		"country1": countries[0] or country1,
		"country2": countries[1] or country2,
		"product": product,
		"year": year,
		"year_start": year_start,
		"year_end": year_end,
		"year_interval": year_interval,
		"trade_flow_list": trade_flow_list,
		"country1_list": country_lists[0],
		"country2_list": country_lists[1],
		"product_list": product_list,
		"year1_list": year1_list,
		"year2_list": year2_list,
		"year_interval_list": year_interval_list,
		"api_uri": api_uri,
		"item_type": item_type}, context_instance=RequestContext(request))

def api_casy(request, trade_flow, country1, year):
	crawler = request.GET.get("_escaped_fragment_", False)
	
	lang = request.session['django_language'] if 'django_language' in request.session else "en"
	lang = request.GET.get("lang", lang)
	
	prod_class = request.session['product_classification'] if 'product_classification' in request.session else "hs4"
	prod_class = request.GET.get("prod_class", prod_class)
	
	query_params = request.GET.copy()
	query_params["lang"] = lang
	query_params["product_classification"] = prod_class
	
	country1 = Country.objects.get(name_3char=country1)
	
	if crawler == "":
		db_response = Sitc4_cpy.objects.casy(country1, trade_flow, year, lang)
		data = [list(x) + [(x[3] / db_response["sum"][x[0]])*100] for x in list(db_response["data"])]
		return [data, db_response["sum"], db_response["columns"]]
	
	json_response = {}
	
	# casy means country1 / all / show / year
	if prod_class == "sitc4":
		json_response["data"] = Sitc4_cpy.objects.casy(country1, trade_flow)
		json_response["attr_data"] = Sitc4.objects.get_all(lang)
	elif prod_class == "hs4":
		json_response["data"] = Hs4_cpy.objects.casy(country1, trade_flow)
		json_response["attr_data"] = Hs4.objects.get_all(lang)
	
	json_response["country1"] = country1.to_json()
	json_response["title"] = "What does %s %s?" % (country1.name, trade_flow.replace("_", " "))
	json_response["year"] = year
	json_response["other"] = query_params
	if "." in year:
		year_parts = [int(x) for x in year.split(".")]
		json_response["year_start"] = year_parts[0]
		json_response["year_end"] = year_parts[1]
		json_response["year_interval"] = year_parts[2]

	return HttpResponse(json.dumps(json_response))

def api_sapy(request, trade_flow, product, year):
	crawler = request.GET.get("_escaped_fragment_", False)
	
	lang = request.session['django_language'] if 'django_language' in request.session else "en"
	lang = request.GET.get("lang", lang)
	
	prod_class = request.session['product_classification'] if 'product_classification' in request.session else "hs4"
	prod_class = request.GET.get("prod_class", prod_class)
	
	query_params = request.GET.copy()
	query_params["lang"] = lang
	query_params["product_classification"] = prod_class
	
	product = Sitc4.objects.get(code=product) if prod_class == "sitc4" else Hs4.objects.get(code=product)
	
	if crawler == "":
		db_response = Sitc4_cpy.objects.sapy(product, trade_flow, year, lang)
		data = [list(x) + [(x[3] / db_response["sum"][x[0]])*100] for x in list(db_response["data"])]
		return [data, db_response["sum"], db_response["columns"]]
	
	json_response = {}
	
	# casy means country1 / all / show / year
	if prod_class == "sitc4":
		json_response["data"] = Sitc4_cpy.objects.sapy(product, trade_flow)
		json_response["attr_data"] = Country.objects.get_all(lang)
	elif prod_class == "hs4":
		json_response["data"] = Hs4_cpy.objects.sapy(product, trade_flow)
		json_response["attr_data"] = Country.objects.get_all(lang)
	json_response["title"] = "Who %ss %s?" % (trade_flow.replace("_", " "), product.name_en)
	json_response["product"] = product.to_json()
	json_response["year"] = year
	json_response["other"] = query_params
	if "." in year:
		year_parts = [int(x) for x in year.split(".")]
		json_response["year_start"] = year_parts[0]
		json_response["year_end"] = year_parts[1]
		json_response["year_interval"] = year_parts[2]
	
	if crawler == "":
		return Sitc4_cpy.objects.sapy(product, trade_flow, year)
	return HttpResponse(json.dumps(json_response))

def api_csay(request, trade_flow, country1, year):
	crawler = request.GET.get("_escaped_fragment_", False)
	
	lang = request.session['django_language'] if 'django_language' in request.session else "en"
	lang = request.GET.get("lang", lang)
	
	prod_class = request.session['product_classification'] if 'product_classification' in request.session else "hs4"
	prod_class = request.GET.get("prod_class", prod_class)
	
	query_params = request.GET.copy()
	query_params["lang"] = lang
	query_params["product_classification"] = prod_class
	
	country1 = Country.objects.get(name_3char=country1)
	
	article = "to" if trade_flow == "export" else "from"
	
	if crawler == "":
		db_response = Sitc4_ccpy.objects.csay(country1, trade_flow, year, lang)
		data = [list(x) + [(x[3] / db_response["sum"][x[0]])*100] for x in list(db_response["data"])]
		return [data, db_response["sum"], db_response["columns"]]
	
	json_response = {}
	
	# csay means country1 / show / all / year
	if prod_class == "sitc4":
		json_response["data"] = Sitc4_ccpy.objects.csay(country1, trade_flow)
	elif prod_class == "hs4":
		json_response["data"] = Hs4_ccpy.objects.csay(country1, trade_flow)
	json_response["attr_data"] = Country.objects.get_all(lang)
	json_response["title"] = "Where does %s %s %s?" % (country1.name, trade_flow, article)
	json_response["country1"] = country1.to_json()
	json_response["year"] = year
	json_response["other"] = query_params
	if "." in year:
		year_parts = [int(x) for x in year.split(".")]
		json_response["year_start"] = year_parts[0]
		json_response["year_end"] = year_parts[1]
		json_response["year_interval"] = year_parts[2]
	
	return HttpResponse(json.dumps(json_response))

def api_ccsy(request, trade_flow, country1, country2, year):
	crawler = request.GET.get("_escaped_fragment_", False)
	
	lang = request.session['django_language'] if 'django_language' in request.session else "en"
	lang = request.GET.get("lang", lang)
	
	prod_class = request.session['product_classification'] if 'product_classification' in request.session else "hs4"
	prod_class = request.GET.get("prod_class", prod_class)
	
	query_params = request.GET.copy()
	query_params["lang"] = lang
	query_params["product_classification"] = prod_class
	
	country1 = Country.objects.get(name_3char=country1)
	country2 = Country.objects.get(name_3char=country2)
	
	article = "to" if trade_flow == "export" else "from"
	
	if crawler == "":
		db_response = Sitc4_ccpy.objects.ccsy(country1, country2, trade_flow, year, lang)
		data = [list(x) + [(x[3] / db_response["sum"][x[0]])*100] for x in list(db_response["data"])]
		return [data, db_response["sum"], db_response["columns"]]
	
	json_response = {}
	
	# ccsy means country1 / countr2 / show / year
	if prod_class == "sitc4":
		json_response["data"] = Sitc4_ccpy.objects.ccsy(country1, country2, trade_flow)
		json_response["attr_data"] = Sitc4.objects.get_all(lang)
	elif prod_class == "hs4":
		json_response["data"] = Hs4_ccpy.objects.ccsy(country1, country2, trade_flow)
		json_response["attr_data"] = Hs4.objects.get_all(lang)
	json_response["title"] = "What does %s %s %s %s?" % (country1.name, trade_flow, article, country2.name)
	json_response["country1"] = country1.to_json()
	json_response["country2"] = country2.to_json()
	json_response["year"] = year
	json_response["other"] = query_params
	if "." in year:
		year_parts = [int(x) for x in year.split(".")]
		json_response["year_start"] = year_parts[0]
		json_response["year_end"] = year_parts[1]
		json_response["year_interval"] = year_parts[2]
		
	return HttpResponse(json.dumps(json_response))

def api_cspy(request, trade_flow, country1, product, year):
	crawler = request.GET.get("_escaped_fragment_", False)
	
	lang = request.session['django_language'] if 'django_language' in request.session else "en"
	lang = request.GET.get("lang", lang)
	
	prod_class = request.session['product_classification'] if 'product_classification' in request.session else "hs4"
	prod_class = request.GET.get("prod_class", prod_class)
	
	query_params = request.GET.copy()
	query_params["lang"] = lang
	query_params["product_classification"] = prod_class
	
	country1 = Country.objects.get(name_3char=country1)
	product = Sitc4.objects.get(code=product) if prod_class == "sitc4" else Hs4.objects.get(code=product)
	
	article = "to" if trade_flow == "export" else "from"
	
	if crawler == "":
		db_response = Sitc4_ccpy.objects.cspy(country1, product, trade_flow, year, lang)
		data = [list(x) + [(x[3] / db_response["sum"][x[0]])*100] for x in list(db_response["data"])]
		return [data, db_response["sum"], db_response["columns"]]
	
	json_response = {}
		
	# cspy means country1 / countr2 / show / year
	if prod_class == "sitc4":
		json_response["data"] = Sitc4_ccpy.objects.cspy(country1, product, trade_flow)
	elif prod_class == "hs4":
		json_response["data"] = Hs4_ccpy.objects.cspy(country1, product, trade_flow)
	json_response["attr_data"] = Country.objects.get_all(lang)
	json_response["title"] = "Where does %s %s %s %s?" % (country1.name, trade_flow, product.name_en, article)
	json_response["country1"] = country1.to_json()
	json_response["product"] = product.to_json()
	json_response["year"] = year
	json_response["other"] = query_params
	if "." in year:
		year_parts = [int(x) for x in year.split(".")]
		json_response["year_start"] = year_parts[0]
		json_response["year_end"] = year_parts[1]
		json_response["year_interval"] = year_parts[2]

	return HttpResponse(json.dumps(json_response))


# Embed for iframe
def embed(request, app_name, trade_flow, country1, country2, product, year):
	lang = request.GET.get("lang", "en")
	query_string = request.GET
	return render_to_response("explore/embed.html", {"app":app_name, "trade_flow": trade_flow, "country1":country1, "country2":country2, "product":product, "year":year, "other":json.dumps(query_string), "lang":lang})

def get_app_type(country1, country2, product, year):
	# country / all / show / year
	if country2 == "all" and product == "show":
		return "casy"
	
	# country / show / all / year
	elif country2 == "show" and product == "all":
		return "csay"
	
	# show / all / product / year
	elif country1 == "show" and country2 == "all":
		return "sapy"
	
	# country / country / show / year
	elif product == "show":
		return "ccsy"
	
	#  country / show / product / year
	else:
		return "cspy"