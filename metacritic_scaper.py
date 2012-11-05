#!/usr/bin/python

import bs4
import csv
import re
import requests
import sys
# from dateutil import parser as date_parser

KINDS = ("any", "movie", "game", "album", "tv") #, "person", "company")
SORTS = ("relevancy", "score", "recent")        
GENRES = {"movie":("action", "adventure", "animation", "biography", "comedy", "crime",
            "documentary", "drama", "family", "fantasy", "film-noir", "history",
            "horror", "music", "musical", "mystery", "news", "reality-tv",
            "romance", "sci-fi", "short", "sport", "thriller", "war", "western"),
          "game":("action", "adventure", "fighting", "first-person", "flight", "party",
            "platformer", "puzzle", "racing","real-time", "role-playing", "simulation",
            "sports", "strategy", "third-person", "turn-based", "wargame", "wrestling"),
          "album":("alt-country", "alternative", "blues", "comedy", "country", "dance",
            "electronic", "experimental", "folk", "house", "indie", "jazz", "latin",
            "metal", "pop", "psychedelic", "punk", "rap", "rb", "reggae", "rock",
            "singer-songwriter", "soul", "soundtrack", "techno", "vocal", "world"),
          "tv":("actionadventure", "animation", "children", "comedy", "drama", "game-shows",
            "moviemini-series", "newsdocumentary", "reality", "science-fiction", "soap",
            "sports", "talk-shows", "variety-shows")}

class MetaCritique:
    def __init__(self):
        self.ID = None
        self.index = None
        self.page = None
        self.title = None
        self.kind = None
        self.url = None
        self.summary = None
        self.metascore = None
        self.userscore = None
        self.critic_count = None
        self.critic_count_positive = None
        self.critic_count_mixed = None
        self.critic_count_negative = None
        self.critic_score_dist = None
        self.user_count = None
        self.user_count_positive = None
        self.user_count_mixed = None
        self.user_count_negative = None
        self.user_score_dist = None
        self.release_date = None
        self.genre = None
        self.platform = None
        self.publisher = None
        self.developer = None
        self.rating = None
        self.cast = None
        self.runtime = None
        self.esrb = None
        self.esrb_reason = None
        self.record_label = None
        self.show_type = None
    def __str__(self) :
        return str(vars(self))


def clean_text_field(text):
    text = re.compile(r'\s{2,}').sub('', text).split(",")
    for item in text :
        item = item.encode("utf-8")
    if len(text) == 1 :
        return text[0]
    else :
        return text


def get_more_stats(tag, name):
    li = tag.find("li", name)
    if li is not None :
        data = li.find("span", class_="data")
        if data is not None :
            text = data.get_text(strip=True)
            if name=="release_date" :
                return text.encode("utf-8")
            else :
                text = clean_text_field(text)
                return text
    else : return None


def get_search_url(query, kind="all") :
    query = query.replace("_","").replace("&","").replace(":","+").replace("-","+").replace(" ","+")
    url = "http://www.metacritic.com/search/%s/%s/results" % (kind, query)
    return url


def DoSearch(search_results, search_params) :
    
    i = 0
    params = search_params.copy()
    pages = int(params["pages"])
    url = "http://www.metacritic.com/search/%s/results" % params["kind"]
    # get rid of these parameters now
    # they mess up metacritic's search results
    del params["kind"]
    del params["pages"]
    
    for pageNum in range(0,pages) :
        
        params["page"] = pageNum
        r = requests.get(url, params=params)
        print "\nINFO: page =", r.url
        
        soup = bs4.BeautifulSoup(r.text)
        results = soup.find_all("li", class_="result")
        for result in results :
            mc = MetaCritique()
            # bookkeeping...
            mc.index = i
            mc.page = pageNum
            
            result_type = result.find("div", class_="result_type")
            if result_type is not None :
                mc.kind = result_type.strong.get_text(strip=True).lower().encode("utf-8")
                span = result_type.find("span")
                if span is not None :
                    mc.platform = span.get_text(strip=True).lower().encode("utf-8")
            
            result_wrap = result.find("div", class_="result_wrap")
            # only results with scores are useful down the line...
            if result_wrap.find("div", class_="basic_stats has_score") is None :
                print "NO SCORE"
                continue
            
            deck = result_wrap.find("p", class_="deck basic_stat")
            if deck is not None :
                mc.summary = deck.get_text(strip=True).encode("utf-8")
            product_title = result_wrap.find("h3", class_="product_title basic_stat")
            if product_title is not None :
                mc.ID = product_title.a["href"][1:].replace("/", "_").encode("utf-8")
                # a necessary check for duplicates
                # quit now if this is already included
                duplicate = False
                for search_result in search_results :
                    if mc.ID == search_result.ID : duplicate = True
                if duplicate is True :
                    print "DUPLICATE"
                    continue
                mc.title = product_title.a.get_text(strip=True).encode("utf-8")
                mc.url = "http://www.metacritic.com" + product_title.a["href"]
            metascore = result_wrap.find("span", class_="metascore")
            if metascore is not None :
                mc.metascore = metascore.get_text(strip=True).encode("utf-8")
                
            more_stats = result_wrap.find("ul", class_="more_stats")
            if more_stats is not None :
                mc.userscore = get_more_stats(more_stats, "product_avguserscore")
                mc.release_date = get_more_stats(more_stats, "release_date")
                mc.esrb = get_more_stats(more_stats, "maturity_rating")
                mc.rating = get_more_stats(more_stats, "rating")
                mc.publisher = get_more_stats(more_stats, "publisher")
                mc.runtime = get_more_stats(more_stats, "runtime")
                mc.cast = get_more_stats(more_stats, "cast")
                mc.genre = get_more_stats(more_stats, "genre")
            
            mc = GetDetails(mc)
            search_results.append(mc)
            i += 1
    
    return search_results


def GetDetails(mc):
    
    print "... ID =", mc.ID
    url = mc.url
    r = requests.get(url)
    soup = bs4.BeautifulSoup(r.text)
    
    main = soup.find("div", id="main", class_="main_col")
    if main is None :
        print "WARNING: bizarre failure at", mc.url
        return mc
    content_head = main.find("div", class_="content_head")
    if content_head is None :
        print "WARNING: bizarre failure at", mc.url
        return mc
        
    product_title = content_head.find("div", class_="product_title")
    if product_title is not None :
        if mc.title is None :
            mc.title = product_title.a.get_text(strip=True)
        platform = product_title.find("span", class_="platform")
        if mc.platform is None and platform is not None :
            mc.platform = platform.get_text(strip=True)
    publisher = content_head.find("li", class_="publisher")
    if mc.publisher is None and publisher is not None :
        mc.publisher = publisher.find("a").get_text(strip=True)
    release_data = content_head.find("li", class_="release_data")
    if mc.release_date is None and release_data is not None :
        data = release_data.find("span", class_="data")
        if data is not None :
            mc.release_date = data.get_text(strip=True)
    
    content_nav = main.find("div", class_="content_nav")
    
    product_data = main.find("div", class_="product_data_summary")
    product_scores = product_data.find("div", class_="product_scores")
    if product_scores is not None :
        metascore_summary = product_scores.find("div", class_="metascore_summary")
        if metascore_summary is not None :
            score_value = metascore_summary.find("span", class_="score_value")
            if mc.metascore is None and score_value is not None :
                mc.metascore = score_value.get_text(strip=True)
            count = metascore_summary.find("span", property="v:count")
            if count is not None :
                mc.critic_count = count.get_text(strip=True)
                
        side_details = product_data.find("div", class_="side_details")
        if side_details is not None :
            userscore = side_details.find("div", class_="avguserscore")
            if userscore is not None :
                score_value = userscore.find("span", class_="score_value")
                if mc.userscore is None and score_value is not None :
                    mc.userscore = score_value.get_text(strip=True)
                count = side_details.find("span", class_="count")
                if count is not None :
                    if count.a is not None :
                        mc.user_count = count.a.get_text(strip=True).split(" ")[0]
                    else :
                        mc.user_count = 0
        
    product_details = product_data.find("div", class_="product_details")
    if product_details is not None :
        side_details = product_details.find("div", class_="side_details")
        if side_details is not None :
            developer = side_details.find("li", class_="developer")
            if developer is not None :
                mc.developer = developer.find("span", class_="data").get_text(strip=True).encode("utf-8")
            product_genre = side_details.find("li", class_="product_genre")
            if mc.genre is None and product_genre is not None :
                mc.genre = clean_text_field(product_genre.find("span", class_="data").get_text(strip=True))
            product_company = side_details.find("li", class_="product_company")
            if product_company is not None :
                mc.record_label = product_company.find("span", class_="data").get_text(strip=True)
            show_type = side_details.find("li", class_="product_show_type")
            if show_type is not None :
                mc.show_type = show_type.find("span", class_="data").get_text(strip=True)
            product_runtime = side_details.find("li", class_="product_runtime")
            if mc.runtime is None and product_runtime is not None :
                mc.runtime = product_runtime.find("span", class_="data").get_text(strip=True)
    
    critic_user_reviews = main.find("div", class_="critic_user_reviews")
    if critic_user_reviews is not None :
        critic_reviews = critic_user_reviews.find("div", class_="critic_reviews_module")
        if critic_reviews is not None :
            score_counts = critic_reviews.find("ol", class_="score_counts")
            if score_counts is not None :
                scores = {}
                # this feels clunky, but whatchagonnado
                for score in score_counts.find_all("li", class_="score_count") :
                    key = score.find("span", class_="label").get_text(strip=True)[:-1].lower().encode("utf-8")
                    val = score.find("span", class_="count").get_text(strip=True).encode("utf-8")
                    if key == "positive" :
                        mc.critic_count_positive = val
                    elif key == "mixed" :
                        mc.critic_count_mixed = val
                    elif key== "negative" :
                        mc.critic_count_negative = val
                    scores[key] = val
                mc.critic_score_dist = scores
        user_reviews = critic_user_reviews.find("div", class_="user_reviews_module")
        if user_reviews is not None :
            score_counts = user_reviews.find("ol", class_="score_counts")
            if score_counts is not None :
                scores = {}
                for score in score_counts.find_all("li", class_="score_count") :
                    key = score.find("span", class_="label").get_text(strip=True)[:-1].lower().encode("utf-8")
                    val = score.find("span", class_="count").get_text(strip=True).encode("utf-8")
                    if key == "positive" :
                        mc.user_count_positive = val
                    elif key == "mixed" :
                        mc.user_count_mixed = val
                    elif key== "negative" :
                        mc.user_count_negative = val
                    scores[key] = val
                mc.user_score_dist = scores
    
    return mc


def SaveToCSV(srs, fileName="test.csv"):
    
    print "\nINFO: Saving to file =", fileName
    
    fileOut = open(fileName, "wt")
    fieldNames = ("index", "page", "ID", "title", "kind", "url",
        "metascore", "critic_count", #"critic_score_dist",
        "critic_count_positive", "critic_count_mixed", "critic_count_negative", 
        "userscore", "user_count", #"user_score_dist",
        "user_count_positive", "user_count_mixed", "user_count_negative", 
        "developer", "publisher", "record_label", "platform", "release_date",
        "rating", "esrb", "esrb_reason",
        "runtime", "genre", "cast", "show_type", "summary")
    writer = csv.DictWriter(fileOut, fieldnames=fieldNames, restval="NA", extrasaction="ignore")   
    headers = dict( (n,n) for n in fieldNames )
    writer.writerow(headers)
    for sr in srs :
        row = vars(sr)
        #print "... ID =", row["ID"]
        for key, value in row.items() :
            if value is None : row[key] = "NA"
        try :
            writer.writerow(row)
        except UnicodeEncodeError :
            print "\nERROR: UnicodeEncode\n", row
        
    print "INFO: File", fileName, "saved"
    fileOut.close()


if __name__ == "__main__" :
    
    print ""
    
    # idiot-proofing
    try : sys.argv[1]
    except IndexError :
        sys.exit("ERROR: Must provide at least one argument! \"kind\" or \"help\"")

    # helpful reminder for those who forget
    if sys.argv[1] == "help" :
        print "INFO: Search parameters"
        print "\tkind =", KINDS
        print "\tsort =", SORTS
        print "\tpages = (1, ..., 50)"
        print "\tgenres =", GENRES
        print "\nExample: > python metacritic_scaper.py kind=movie sort=relevancy pages=1 genres=action"
        sys.exit("")
    
    # get search parameters
    search_params = {"search_type":"advanced"}
    for arg in sys.argv[1:] :
        key = arg.split("=")[0]
        val = arg.split("=")[1]
        if key == "kind" :
            if val in KINDS : search_params[key] = val
            else : print "WARNING: Invalid kind =", val
        elif key == "sort" :
            if val in SORTS : search_params[key] = val
            else : print "WARNING: Invalid sort =", val
        elif key == "pages":
            if int(val) >= 1 and int(val) <= 50 : search_params[key] = val
            else : print "WARNING: Invalid page =", val
        elif key == "genres" :
            try :
                kind = search_params["kind"]
            except KeyError :
                print "WARNING: Must pass (valid) kind before genres!"
                continue
            if val in GENRES[kind] :
                search_params[key] = val
            elif val == "all" :
                search_params[key] = GENRES[kind]
            else :
                print "WARNING: Invalid genres", val, "for kind", kind
        else : print "WARNING: Invalid search parameter", key
    
    # set defaults search parameters
    # and construct output file name
    fileName = ""
    try : fileName += search_params["kind"] + "_"
    except KeyError :
        search_params["kind"] = "all"
        fileName += search_params["kind"] + "_"
    try : fileName += search_params["genres"] + "_"
    except TypeError :
        fileName += "all_"
    except KeyError :
        fileName += "any_"
        print "WARNING: genre not specified!"
    try : fileName += search_params["sort"] + "_"
    except KeyError :
        search_params["sort"] = "relevancy"
        fileName += search_params["sort"] + "_"
        print "WARNING: sort=relevancy by default!"
    try : fileName += search_params["pages"] + "_"
    except KeyError :
        search_params["pages"] = "1"
        fileName += search_params["pages"] + "_"
        print "WARNING: pages=1 by default!"
    fileName += ".csv"
    fileName = fileName.replace("_.csv", ".csv")
    
    print "\nINFO: Search parameters =", search_params
    
    # fetch and scrape metacritic search results!
    search_results = []
    # HACK: special case for genres=all
    if isinstance(search_params["genres"], tuple) is True :
        for genre in search_params["genres"] :
            search_params_copy = search_params.copy()
            search_params_copy["genres"] = genre
            search_results = DoSearch(search_results, search_params_copy)
    else :
        search_results = DoSearch(search_results, search_params)
        
    print "\nINFO: Number of search results =", len(search_results)

    # output in csv format for R
    SaveToCSV(search_results, fileName=fileName)
    

