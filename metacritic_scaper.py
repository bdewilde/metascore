#!/usr/bin/python

from dateutil import parser as date_parser
import re
import requests
import urllib2
import bs4
import sys

KINDS = ("all", "movie", "game", "album", "tv", "person", "company")
SORTS = ("relevancy", "recent", "score")

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
        self.critic_score_dist = None
        self.user_count = None
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
                return text
            else :
                text = clean_text_field(text)
                return text
    else : return None


def get_search_url(query, kind="all") :
    query = query.replace("_","").replace("&","").replace(":","+").replace("-","+").replace(" ","+")
    url = "http://www.metacritic.com/search/%s/%s/results" % (kind, query)
    return url


def Search(kind="all", sort='relevancy', pages=1) :
    
    mcs = []
    i = 0
    for pageNum in range(0,pages) :
        url = "http://www.metacritic.com/search/%s/results" % kind
        params = {'search_type':'advanced', 'sort':sort, 'page':pageNum}
        r = requests.get(url, params=params)
        print "\nPAGE =", r.url
        
        soup = bs4.BeautifulSoup(r.text)
        results = soup.find_all("li", class_="result")
        for result in results :
            mc = MetaCritique()
            mc.index = i
            mc.page = pageNum
            
            result_type = result.find("div", class_="result_type")
            if result_type is not None :
                mc.kind = result_type.strong.get_text(strip=True).lower()
                span = result_type.find("span")
                if span is not None :
                    mc.platform = span.get_text(strip=True).lower()
            
            result_wrap = result.find("div", class_="result_wrap")
            # only results with scores are useful down the line...
            if result_wrap.find("div", class_="basic_stats has_score") is None : continue
            
            deck = result_wrap.find("p", class_="deck basic_stat")
            if deck is not None :
                mc.summary = deck.get_text(strip=True)
            product_title = result_wrap.find("h3", class_="product_title basic_stat")
            if product_title is not None :
                mc.ID = product_title.a["href"][1:].replace("/", "_")
                mc.title = product_title.a.get_text(strip=True)
                mc.url = "http://www.metacritic.com" + product_title.a["href"]
            metascore = result_wrap.find("span", class_="metascore")
            if metascore is not None :
                mc.metascore = metascore.get_text(strip=True)
                
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
            mcs.append(mc)
            i += 1
            
    return mcs


def GetDetails(mc):
    
    print "... ID =", mc.ID
    url = mc.url
    r = requests.get(url)
    soup = bs4.BeautifulSoup(r.text)
    
    main = soup.find("div", id="main", class_="main_col")
    
    content_head = main.find("div", class_="content_head")
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
                mc.developer = developer.find("span", class_="data").get_text(strip=True)
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
                for score in score_counts.find_all("li", class_="score_count") :
                    key = score.find("span", class_="label").get_text(strip=True)[:-1].lower()
                    val = score.find("span", class_="count").get_text(strip=True)
                    scores[key] = val
                mc.critic_score_dist = scores
        user_reviews = critic_user_reviews.find("div", class_="user_reviews_module")
        if user_reviews is not None :
            score_counts = user_reviews.find("ol", class_="score_counts")
            if score_counts is not None :
                scores = {}
                for score in score_counts.find_all("li", class_="score_count") :
                    key = score.find("span", class_="label").get_text(strip=True)[:-1].lower()
                    val = score.find("span", class_="count").get_text(strip=True)
                    scores[key] = val
                mc.user_score_dist = scores
    
    return mc


def SaveToCSV(sr):
    pass


if __name__ == "__main__" :
    
    print "SEARCH OPTIONS"
    print "... KINDS :", KINDS
    print "... SORTS :", SORTS
    print "... PAGES : 1-50\n"
    if len(sys.argv) == 1 :
        print "Search(type=all, sort=relevancy, pages=1)\n"
        search_results = Search()
    if len(sys.argv) == 2 :
        print "Search(type="+sys.argv[1]+", sort=relevancy, pages=1)\n"
        search_results = Search(sys.argv[1])
    elif len(sys.argv) == 3 :
        print "Search(type="+sys.argv[1]+", sort="+sys.argv[2]+", pages=1)\n"
        search_results = Search(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 4 :
        print "Search(type=" + sys.argv[1] + ", sort=" + sys.argv[2] + ", pages=" + sys.argv[3] + ")\n"
        search_results = Search(sys.argv[1], sys.argv[2], int(sys.argv[3]))
    #print "Number of search results:", len(search_results), "\n"
    
    test = search_results[0]
    print test
    
    #for search_result in search_results :
    #print search_result, "\n"
