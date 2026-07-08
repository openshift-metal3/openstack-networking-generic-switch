#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import enum


class NetconfEditConfigOperation(enum.Enum):
    """RFC 6241 - <edit-config> operation attribute

    The "operation" attribute has one of the following values:
         merge:  The configuration data identified by the element
            containing this attribute is merged with the configuration
            at the corresponding level in the configuration datastore
            identified by the <target> parameter.  This is the default
            behavior.
         replace:  The configuration data identified by the element
            containing this attribute replaces any related configuration
            in the configuration datastore identified by the <target>
            parameter.  If no such configuration data exists in the
            configuration datastore, it is created.  Unlike a
            <copy-config> operation, which replaces the entire target
            configuration, only the configuration actually present in
            the <config> parameter is affected.
         create:  The configuration data identified by the element
            containing this attribute is added to the configuration if
            and only if the configuration data does not already exist in
            the configuration datastore.  If the configuration data
            exists, an <rpc-error> element is returned with an
            <error-tag> value of "data-exists".
         delete:  The configuration data identified by the element
            containing this attribute is deleted from the configuration
            if and only if the configuration data currently exists in
            the configuration datastore.  If the configuration data does
            not exist, an <rpc-error> element is returned with an
            <error-tag> value of "data-missing".
         remove:  The configuration data identified by the element
            containing this attribute is deleted from the configuration
            if the configuration data currently exists in the
            configuration datastore.  If the configuration data does not
            exist, the "remove" operation is silently ignored by the
            server.
    """
    MERGE = 'merge'
    REPLACE = 'replace'
    CREATE = 'create'
    DELETE = 'delete'
    REMOVE = 'remove'


CFG_ELEMENT = 'config'

LOCK_DENIED_TAG = 'lock-denied'  # [RFC 4741]
CANDIDATE = 'candidate'
RUNNING = 'running'
STARTUP = 'startup'
DEFERRED = 'deferred'

IANA_NETCONF_CAPABILITIES = {
    # [RFC4741][RFC6241]
    ':base:1.0':
        'urn:ietf:params:netconf:base:1.0',
    # [RFC4741]
    ':confirmed-commit':
        'urn:ietf:params:netconf:capability:confirmed-commit:1.0',
    ':validate':
        'urn:ietf:params:netconf:capability:validate:1.0',
    # [RFC6241]
    ':base:1.1':
        'urn:ietf:params:netconf:base:1.1',
    ':writable-running':
        'urn:ietf:params:netconf:capability:writable-running:1.0',
    ':candidate':
        'urn:ietf:params:netconf:capability:candidate:1.0',
    ':confirmed-commit:1.1':
        'urn:ietf:params:netconf:capability:confirmed-commit:1.1',
    ':rollback-on-error':
        'urn:ietf:params:netconf:capability:rollback-on-error:1.0',
    ':validate:1.1':
        'urn:ietf:params:netconf:capability:validate:1.1',
    ':startup':
        'urn:ietf:params:netconf:capability:startup:1.0',
}
