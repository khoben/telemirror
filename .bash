# set heroku env from .env file
heroku config:set $(cat .env | sed '/^$/d; /#[[:print:]]*$/d')