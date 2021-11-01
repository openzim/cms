import querystring from 'querystring'

export default {
  backend_api: window.environ.BACKEND_API || "https://api.cms.openzim.org/v1",
  params_serializer: function(params) { // turn javascript params object into querystring
    return querystring.stringify(params);
  },
}
