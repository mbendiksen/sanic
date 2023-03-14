from __future__ import annotations

import re
import string
import sys
from datetime import datetime
from http import cookies as http_cookies
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, overload

from sanic.exceptions import ServerError
from sanic.log import deprecation

if TYPE_CHECKING:
    from sanic.compat import Header

if sys.version_info < (3, 8):  # no cov
    SameSite = str
    LiteralRootPath = str
    LiteralTrue = bool
    LiteralFalse = bool
else:  # no cov
    from typing import Literal

    LiteralRootPath = Literal["/"]
    LiteralTrue = Literal[True]
    LiteralFalse = Literal[False]
    SameSite = Union[
        Literal["Strict"],
        Literal["Lax"],
        Literal["None"],
        Literal["strict"],
        Literal["lax"],
        Literal["none"],
    ]

DEFAULT_MAX_AGE = 0
SAMESITE_VALUES = ("strict", "lax", "none")
COOKIE_NAME_RESERVED_CHARS = re.compile(
    '[\x00-\x1F\x7F-\xFF()<>@,;:\\\\"/[\\]?={} \x09]'
)
LEGAL_CHARS = string.ascii_letters + string.digits + "!#$%&'*+-.^_`|~:"
UNESCAPED_CHARS = LEGAL_CHARS + " ()/<=>?@[]{}"
TRANSLATOR = {
    n: "\\%03o" % n for n in set(range(256)) - set(map(ord, UNESCAPED_CHARS))
}
TRANSLATOR.update({ord('"'): '\\"', ord("\\"): "\\\\"})


def _quote(str):
    r"""Quote a string for use in a cookie header.
    If the string does not need to be double-quoted, then just return the
    string.  Otherwise, surround the string in doublequotes and quote
    (with a \) special characters.
    """
    if str is None or _is_legal_key(str):
        return str
    else:
        return '"' + str.translate(TRANSLATOR) + '"'


_is_legal_key = re.compile("[%s]+" % re.escape(LEGAL_CHARS)).fullmatch


def parse_cookie(raw: str):
    cookies: Dict[str, List] = {}

    for token in raw.split(";"):
        name, __, value = token.partition("=")
        name = name.strip()
        value = value.strip()

        if not name:
            continue

        if COOKIE_NAME_RESERVED_CHARS.search(name):
            continue

        if len(value) > 2 and value[0] == '"' and value[-1] == '"':
            value = http_cookies._unquote(value)

        if name in cookies:
            cookies[name].append(value)
        else:
            cookies[name] = [value]

    return cookies


# In v23.9, we should remove this as being a subclass of dict
class CookieJar(dict):
    """
    CookieJar dynamically writes headers as cookies are added and removed
    It gets around the limitation of one header per name by using the
    MultiHeader class to provide a unique key that encodes to Set-Cookie.
    """

    HEADER_KEY = "Set-Cookie"

    def __init__(self, headers: Header):
        super().__init__()
        self.headers = headers

    def __setitem__(self, key, value):
        # If this cookie doesn't exist, add it to the header keys
        deprecation(
            "Setting cookie values using the dict pattern has been "
            "deprecated. You should instead use the cookies.add_cookie "
            "method. To learn more, please see: ___.",
            0,
        )
        if key not in self:
            self.add_cookie(key, value, secure=False, samesite=None)
        else:
            self[key].value = value

    def __delitem__(self, key):
        deprecation(
            "Deleting cookie values using the dict pattern has been "
            "deprecated. You should instead use the cookies.delete_cookie "
            "method. To learn more, please see: ___.",
            0,
        )
        if key in self:
            super().__delitem__(key)
        self.delete_cookie(key)

    def __len__(self):
        return len(self.cookies)

    def __getitem__(self, key: str) -> Cookie:
        deprecation(
            "Accessing cookies from the CookieJar by dict key is deprecated. "
            "You should instead use the cookies.get_cookie method. "
            "To learn more, please see: ___.",
            0,
        )
        return super().__getitem__(key)

    def __iter__(self):
        deprecation(
            "Iterating over the CookieJar has been deprecated and will be "
            "removed in v23.9. To learn more, please see: ___.",
            23.9,
        )
        return super().__iter__()

    def keys(self):
        deprecation(
            "Accessing CookieJar.keys() has been deprecated and will be "
            "removed in v23.9. To learn more, please see: ___.",
            23.9,
        )
        return super().keys()

    def values(self):
        deprecation(
            "Accessing CookieJar.values() has been deprecated and will be "
            "removed in v23.9. To learn more, please see: ___.",
            23.9,
        )
        return super().values()

    def items(self):
        deprecation(
            "Accessing CookieJar.items() has been deprecated and will be "
            "removed in v23.9. To learn more, please see: ___.",
            23.9,
        )
        return super().items()

    def get(self, *args, **kwargs):
        deprecation(
            "Accessing cookies from the CookieJar using get is deprecated "
            "and will be removed in v23.9. You should instead use the "
            "cookies.get_cookie method. To learn more, please see: ___.",
            23.9,
        )
        return super().get(*args, **kwargs)

    def pop(self, key, *args, **kwargs):
        deprecation(
            "Using CookieJar.pop() has been deprecated and will be "
            "removed in v23.9. To learn more, please see: ___.",
            23.9,
        )
        self.delete(key)
        return super().pop(key, *args, **kwargs)

    @property
    def header_key(self):
        deprecation(
            "The CookieJar.header_key property has been deprecated and will "
            "be removed in version 23.9. Use CookieJar.HEADER_KEY. ",
            23.9,
        )
        return CookieJar.HEADER_KEY

    @property
    def cookie_headers(self) -> Dict[str, str]:
        deprecation(
            "The CookieJar.coookie_headers property has been deprecated "
            "and will be removed in version 23.9. If you need to check if a "
            "particular cookie key has been set, use CookieJar.has_cookie.",
            23.9,
        )
        return {key: self.header_key for key in self}

    @property
    def cookies(self) -> List[Cookie]:
        return self.headers.getall(self.HEADER_KEY)

    def get_cookie(
        self, key: str, path: str = "/", domain: Optional[str] = None
    ) -> Optional[Cookie]:
        for cookie in self.cookies:
            if (
                cookie.key == key
                and cookie.path == path
                and cookie.domain == domain
            ):
                return cookie
        return None

    def has_cookie(
        self, key: str, path: str = "/", domain: Optional[str] = None
    ) -> bool:
        for cookie in self.cookies:
            if (
                cookie.key == key
                and cookie.path == path
                and cookie.domain == domain
            ):
                return True
        return False

    # When using secure_prefix=True
    @overload
    def add_cookie(
        self,
        key: str,
        value: str,
        *,
        path: str = "/",
        domain: Optional[str] = None,
        secure: LiteralTrue = True,
        max_age: Optional[int] = None,
        expires: Optional[datetime] = None,
        httponly: bool = False,
        samesite: Optional[SameSite] = "Lax",
        partitioned: bool = False,
        comment: Optional[str] = None,
        host_prefix: LiteralFalse = False,
        secure_prefix: LiteralTrue = True,
    ) -> Cookie:
        ...

    # When using host_prefix=True
    @overload
    def add_cookie(
        self,
        key: str,
        value: str,
        *,
        path: LiteralRootPath = "/",
        domain: None = None,
        secure: LiteralTrue = True,
        max_age: Optional[int] = None,
        expires: Optional[datetime] = None,
        httponly: bool = False,
        samesite: Optional[SameSite] = "Lax",
        partitioned: bool = False,
        comment: Optional[str] = None,
        host_prefix: LiteralTrue = True,
        secure_prefix: LiteralFalse = False,
    ) -> Cookie:
        ...

    def add_cookie(
        self,
        key: str,
        value: str,
        *,
        path: str = "/",
        domain: Optional[str] = None,
        secure: bool = True,
        max_age: Optional[int] = None,
        expires: Optional[datetime] = None,
        httponly: bool = False,
        samesite: Optional[SameSite] = "Lax",
        partitioned: bool = False,
        comment: Optional[str] = None,
        host_prefix: bool = False,
        secure_prefix: bool = False,
    ) -> Cookie:
        """
        Add a cookie to the CookieJar

        :param key: Key of the cookie
        :type key: str
        :param value: Value of the cookie
        :type value: str
        :param path: Path of the cookie, defaults to None
        :type path: Optional[str], optional
        :param domain: Domain of the cookie, defaults to None
        :type domain: Optional[str], optional
        :param secure: Whether to set it as a secure cookie, defaults to True
        :type secure: bool
        :param max_age: Max age of the cookie in seconds; if set to 0 a
            browser should delete it, defaults to None
        :type max_age: Optional[int], optional
        :param expires: When the cookie expires; if set to None browsers
            should set it as a session cookie, defaults to None
        :type expires: Optional[datetime], optional
        :param httponly: Whether to set it as HTTP only, defaults to False
        :type httponly: bool
        :param samesite: How to set the samesite property, should be
            strict, lax or none (case insensitive), defaults to Lax
        :type samesite: Optional[SameSite], optional
        :param partitioned: Whether to set it as partitioned, defaults to False
        :type partitioned: bool
        :param comment: A cookie comment, defaults to None
        :type comment: Optional[str], optional
        :param host_prefix: Whether to add __Host- as a prefix to the key.
            This requires that path="/", domain=None, and secure=True,
            defaults to False
        :type host_prefix: bool
        :param secure_prefix: Whether to add __Secure- as a prefix to the key.
            This requires that secure=True, defaults to False
        :type secure_prefix: bool
        :return: The instance of the created cookie
        :rtype: Cookie
        """
        cookie = Cookie(
            key,
            value,
            path=path,
            expires=expires,
            comment=comment,
            domain=domain,
            max_age=max_age,
            secure=secure,
            httponly=httponly,
            samesite=samesite,
            partitioned=partitioned,
            host_prefix=host_prefix,
            secure_prefix=secure_prefix,
        )
        self.headers.add(self.HEADER_KEY, cookie)

        # This should be removed in v23.9
        super().__setitem__(key, cookie)

        return cookie

    def delete_cookie(
        self,
        key: str,
        *,
        path: str = "/",
        domain: Optional[str] = None,
    ) -> None:
        """
        Delete a cookie

        This will effectively set it as Max-Age: 0, which a browser should
        interpret it to mean: "delete the cookie".

        Since it is a browser/client implementation, your results may vary
        depending upon which client is being used.

        :param key: The key to be deleted
        :type key: str
        """
        # remove it from header
        cookies: List[Cookie] = self.headers.popall(self.HEADER_KEY, [])
        for cookie in cookies:
            if (
                cookie.key != key
                or cookie.path != path
                or cookie.domain != domain
            ):
                self.headers.add(self.HEADER_KEY, cookie)

        # This should be removed in v23.9
        try:
            super().__delitem__(key)
        except KeyError:
            ...

        self.add_cookie(
            key=key,
            value="",
            path=path,
            domain=domain,
            max_age=0,
            samesite=None,
        )


# In v23.9, we should remove this as being a subclass of dict
# Instead, it should be an object with __slots__
# All of the current property accessors should be removed in favor
# of actual slotted properties.
class Cookie(dict):
    """A stripped down version of Morsel from SimpleCookie"""

    HOST_PREFIX = "__Host-"
    SECURE_PREFIX = "__Secure-"

    _keys = {
        "path": "Path",
        "comment": "Comment",
        "domain": "Domain",
        "max-age": "Max-Age",
        "expires": "expires",
        "samesite": "SameSite",
        "version": "Version",
        "secure": "Secure",
        "httponly": "HttpOnly",
        "partitioned": "Partitioned",
    }
    _flags = {"secure", "httponly", "partitioned"}

    def __init__(
        self,
        key: str,
        value: str,
        *,
        path: str = "/",
        domain: Optional[str] = None,
        secure: bool = True,
        max_age: Optional[int] = None,
        expires: Optional[datetime] = None,
        httponly: bool = False,
        samesite: Optional[SameSite] = "Lax",
        partitioned: bool = False,
        comment: Optional[str] = None,
        host_prefix: bool = False,
        secure_prefix: bool = False,
    ):
        if key in self._keys:
            raise KeyError("Cookie name is a reserved word")
        if not _is_legal_key(key):
            raise KeyError("Cookie key contains illegal characters")
        if host_prefix and secure_prefix:
            raise ServerError(
                "Both host_prefix and secure_prefix were requested. "
                "A cookie should have only one prefix."
            )
        elif host_prefix:
            if not secure:
                raise ServerError(
                    "Cannot set host_prefix on a cookie without secure=True"
                )
            if path != "/":
                raise ServerError(
                    "Cannot set host_prefix on a cookie unless path='/'"
                )
            if domain:
                raise ServerError(
                    "Cannot set host_prefix on a cookie with a defined domain"
                )
            key = self.HOST_PREFIX + key
        elif secure_prefix:
            if not secure:
                raise ServerError(
                    "Cannot set secure_prefix on a cookie without secure=True"
                )
            key = self.SECURE_PREFIX + key
        if partitioned and not host_prefix:
            # This is technically possible, but it is not advisable so we will
            # take a stand and say "don't shoot yourself in the foot"
            raise ServerError(
                "Cannot create a partitioned cookie without "
                "also setting host_prefix=True"
            )

        self.key = key
        self.value = value
        super().__init__()
        self._set_value("path", path)
        self._set_value("expires", expires)
        self._set_value("comment", comment)
        self._set_value("domain", domain)
        self._set_value("max-age", max_age)
        self._set_value("secure", secure)
        self._set_value("httponly", httponly)
        self._set_value("samesite", samesite)
        self._set_value("partitioned", partitioned)

    def __setitem__(self, key, value):
        deprecation(
            "Setting values on a Cookie object as a dict has been deprecated. "
            "This feature will be removed in v23.9. You should instead set "
            f"values on cookies as object properties: cookie.{key}=... ",
            23.9,
        )
        self._set_value(key, value)

    # This is a temporary method for backwards compat and should be removed
    # in v23.9 when this is no longer a dict
    def _set_value(self, key: str, value: Any) -> None:
        if key not in self._keys:
            raise KeyError("Unknown cookie property")

        if value is not None:
            if key.lower() == "max-age" and not str(value).isdigit():
                raise ValueError("Cookie max-age must be an integer")
            elif key.lower() == "expires" and not isinstance(value, datetime):
                raise TypeError("Cookie 'expires' property must be a datetime")
            elif key.lower() == "samesite":
                if value.lower() not in SAMESITE_VALUES:
                    raise TypeError(
                        "Cookie 'samesite' property must "
                        f"be one of: {','.join(SAMESITE_VALUES)}"
                    )
                value = value.title()

        super().__setitem__(key, value)

    def encode(self, encoding):
        """
        Encode the cookie content in a specific type of encoding instructed
        by the developer. Leverages the :func:`str.encode` method provided
        by python.

        This method can be used to encode and embed ``utf-8`` content into
        the cookies.

        :param encoding: Encoding to be used with the cookie
        :return: Cookie encoded in a codec of choosing.
        :except: UnicodeEncodeError
        """
        return str(self).encode(encoding)

    def __str__(self):
        """Format as a Set-Cookie header value."""
        output = ["%s=%s" % (self.key, _quote(self.value))]
        key_index = list(self._keys)
        for key, value in sorted(
            self.items(), key=lambda x: key_index.index(x[0])
        ):
            if value is not None and value is not False:
                if key == "max-age":
                    try:
                        output.append("%s=%d" % (self._keys[key], value))
                    except TypeError:
                        output.append("%s=%s" % (self._keys[key], value))
                elif key == "expires":
                    output.append(
                        "%s=%s"
                        % (
                            self._keys[key],
                            value.strftime("%a, %d-%b-%Y %T GMT"),
                        )
                    )
                elif key in self._flags:
                    output.append(self._keys[key])
                else:
                    output.append("%s=%s" % (self._keys[key], value))

        return "; ".join(output)

    @property
    def path(self) -> str:
        return self["path"]

    @path.setter
    def path(self, value: str) -> None:
        self._set_value("path", value)

    @property
    def expires(self) -> Optional[datetime]:
        return self.get("expires")

    @expires.setter
    def expires(self, value: datetime) -> None:
        self._set_value("expires", value)

    @property
    def comment(self) -> Optional[str]:
        return self.get("comment")

    @comment.setter
    def comment(self, value: str) -> None:
        self._set_value("comment", value)

    @property
    def domain(self) -> Optional[str]:
        return self.get("domain")

    @domain.setter
    def domain(self, value: str) -> None:
        self._set_value("domain", value)

    @property
    def max_age(self) -> Optional[int]:
        return self.get("max-age")

    @max_age.setter
    def max_age(self, value: int) -> None:
        self._set_value("max-age", value)

    @property
    def secure(self) -> bool:
        return self.get("secure", False)

    @secure.setter
    def secure(self, value: bool) -> None:
        self._set_value("secure", value)

    @property
    def httponly(self) -> bool:
        return self.get("httponly", False)

    @httponly.setter
    def httponly(self, value: bool) -> None:
        self._set_value("httponly", value)

    @property
    def samesite(self) -> Optional[SameSite]:
        return self.get("samesite")

    @samesite.setter
    def samesite(self, value: SameSite) -> None:
        self._set_value("samesite", value)

    @property
    def partitioned(self) -> bool:
        return self.get("partitioned", False)

    @partitioned.setter
    def partitioned(self, value: bool) -> None:
        self._set_value("partitioned", value)
