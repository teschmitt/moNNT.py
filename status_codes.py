from string import Template

from utils import get_version


class StatusCodes:
    # string literals
    ERR_AUTH_NO_PERMISSION: str = "502 No permission"
    ERR_CMDSYNTAXERROR: str = "501 command syntax error (or un-implemented option)"
    ERR_NOARTICLERETURNED: str = "420 No article(s) selected"
    ERR_NOARTICLESELECTED: str = "420 no current article has been selected"
    ERR_NODESCAVAILABLE: str = "481 Groups and descriptions unavailable"
    ERR_NOGROUPSELECTED: str = "412 no newsgroup has been selected"
    ERR_NOIHAVEHERE: str = "435 article not wanted - do not send it"
    ERR_NONEXTARTICLE: str = "421 no next article in this group"
    ERR_NOPREVIOUSARTICLE: str = "422 no previous article in this group"
    ERR_NOSTREAM: str = "500 Command not understood"
    ERR_NOSUCHARTICLE: str = "430 no such article"
    ERR_NOSUCHARTICLENUM: str = "423 no such article in this group"
    ERR_NOARTICLESINRANGE: str = "423 No articles in that range"
    ERR_NOSUCHGROUP: str = "411 no such news group"
    ERR_NOTCAPABLE: str = "500 command not recognized"
    ERR_NOTPERFORMED: str = "503 program error, function not performed"
    ERR_POSTINGFAILED: str = "441 Posting failed"
    STATUS_AUTH_ACCEPTED: str = "281 Authentication accepted"
    STATUS_AUTH_CONTINUE: str = "381 More authentication information required"
    STATUS_AUTH_REQUIRED: str = "480 Authentication required"
    STATUS_CLOSING: str = "205 closing connection - goodbye!"
    STATUS_EXTENSIONS: str = "215 Extensions supported by server."
    STATUS_HEADERS_FOLLOW: str = "225 Headers follow (multi-line)"
    STATUS_HELPMSG: str = "100 Help text follows (multi-line)"
    STATUS_LIST: str = "215 list of newsgroups follows"
    STATUS_LISTNEWSGROUPS: str = "215 information follows"
    STATUS_LISTSUBSCRIPTIONS: str = "215 list of default newsgroups follows"
    STATUS_NEWGROUPS: str = "231 list of new newsgroups follows"
    STATUS_NEWNEWS: str = "230 List of new articles follows (multi-line)"
    STATUS_NOPOSTMODE: str = "201 Hello, you can't post"
    STATUS_OVERVIEWFMT: str = "215 information follows"
    STATUS_POSTALLOWED: str = "200 Hello, you can post"
    STATUS_POSTSUCCESSFUL: str = "240 Article received ok"
    STATUS_READONLYSERVER: str = "440 Posting not allowed"
    STATUS_SENDARTICLE: str = "340 Send article to be posted"
    STATUS_SERVER_VERSION: str = f"200 Papercut {get_version()}"
    STATUS_SLAVE: str = "202 slave status noted"
    STATUS_XGTITLE: str = "282 list of groups and descriptions follows"
    STATUS_XHDR: str = "221 Header follows"
    STATUS_XOVER: str = "224 Overview information follows"
    STATUS_XPAT: str = "221 Header follows"

    # string templates
    ERR_TIMEOUT: Template = Template("503 Timeout after %seconds seconds, closing connection.")
    STATUS_ARTICLE: Template = Template("220 $number $message_id All of the article follows")
    STATUS_NEXTLAST: Template = Template("223 $number $message_id Article found")
    STATUS_BODY: Template = Template("222 $number $message_id article retrieved - body follows")
    STATUS_DATE: Template = Template("111 $date")
    STATUS_GROUPSELECTED: Template = Template("211 $count $first $last $name group selected")
    STATUS_HEAD: Template = Template("221 $number $message_id article retrieved - head follows")
    STATUS_LISTGROUP: Template = Template("211 $number $low $high $group")
    STATUS_READYNOPOST: Template = Template(
        "200 $url moNNT.py $version server ready (no posting allowed)"
    )
    STATUS_READYOKPOST: Template = Template(
        "200 $url moNNT.py $version server ready (posting allowed)"
    )
    STATUS_STAT: Template = Template("223 $number $message_id Article exists")
