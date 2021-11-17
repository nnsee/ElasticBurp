# ElasticBurp

Scared about the weak searching performance of Burp Suite? Are you missing possibilities to search in Burp? ElasticBurp
combines Burp Suite with the search power of ElasticSearch.


### Installation

1. Install ElasticSearch and Kibana.
2. Configure both - For security reasons it is recommend to let them listen on localhost:
  * Set `network.host: 127.0.0.1` in `/etc/elasticsearch/elasticsearch.yml`.
  * Set `host: "127.0.0.1"` in `/opt/kibana/config/kibana.yml`.
3. Install dependencies in the Jython environment used by Burp Extender with: `$JYTHON_PATH/bin/pip install -r
   requirements.txt`
4. Load ElasticBurp.py as Python extension in Burp Extender.

### Usage

See [this blog article](https://patzke.org/an-introduction-to-wase-and-elasticburp.html) for usage examples.

## WASEQuery

Search ElasticSearch indices created by WASE for

* responses with missing headers
* responses with missing parameters
* all values that were set for a header (e.g. X-Frame-Options, X-XSS-Protection, X-Content-Type-Options, Content-Security-Policy, ...)

...or do arbitrary search queries.

Invoke WASEQuery.py for help message. [This blog
article](https://patzke.org/analyzing-web-application-test-data-with-wasequery.html) shows some examples for usage of
WASEQuery.
