devhub
====

Simple search enabled web app to post dev related content with GitHub auth enabled.
--------


**Dependencies:**

 - Redis
 - ElasticSearch
 - Setup OAuth Applications in GitHub


**Variables to set before running if other than localhost:**

	# Post URL
	url = 'http://localhost:8080/posts/'

	# Environmental variables for Github OAuth keys
	GITHUB_CLIENT_ID = os.environ['GITHUB_CLIENT_ID']
	GITHUB_CLIENT_SECRET = os.environ['GITHUB_CLIENT_SECRET']

![Alt text](https://github.com/marshyski/devhub/blob/master/imgs/Index.png?raw=true)
![Alt text](https://github.com/marshyski/devhub/blob/master/imgs/NewPost.png?raw=true)
![Alt text](https://github.com/marshyski/devhub/blob/master/imgs/Post.png?raw=true)
![Alt text](https://github.com/marshyski/devhub/blob/master/imgs/SearchResult.png?raw=true)
