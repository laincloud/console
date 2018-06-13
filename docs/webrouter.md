```
curl webrouter.${LAIN_DOMAIN}/ab_admin?action=policy_set -d '{"divtype":"uidsuffix","divdata":[{"suffix":"1","upstream":"beta1"}]}'
{"desc":"success  the id of new policy is 0","code":200}
curl "webrouter.${LAIN_DOMAIN}/ab_admin?action=policy_get&policyid=0"
{"data":{"divtype":"uidsuffix","divdata":["1","beta1"]},"desc":"success ","code":200}

curl webrouter.${LAIN_DOMAIN}/ab_admin?action=policy_check -d '{"divtype":"uidsuffix","divdata":[{"suffix":"1","upstream":"beta1"}]}'
{"desc":"success ","code":200}
curl webrouter.${LAIN_DOMAIN}/ab_admin?action=policy_set -d '{"divtype":"uidsuffix","divdata":[{"suffix":"1","upstream":"beta1"}]}'
{"desc":"success  the id of new policy is 0","code":200}
curl "webrouter.${LAIN_DOMAIN}/ab_admin?action=policy_get&policyid=0"
{"data":{"divtype":"uidsuffix","divdata":["1","beta1"]},"desc":"success ","code":200}
curl "webrouter.${LAIN_DOMAIN}/ab_admin?action=policy_del&policyid=0"
{"desc":"success ","code":200}
curl "webrouter.${LAIN_DOMAIN}/ab_admin?action=runtime_set&hostname=test.${LAIN_DOMAIN}&policyid=0"
{"desc":"success ","code":200}
curl "webrouter.${LAIN_DOMAIN}/ab_admin?action=runtime_get&hostname=test.${LAIN_DOMAIN}"
{"data":{"divsteps":1,"runtimegroup":{"first":{"divModulename":"abtesting.diversion.uidsuffix","userInfoModulename":"abtesting.userinfo.uidParser","divDataKey":"ab:policies:1:divdata"}}},"desc":"success ","code":200}
curl "webrouter.${LAIN_DOMAIN}/ab_admin?action=runtime_del&hostname=test.${LAIN_DOMAIN}"
{"desc":"success ","code":200}

curl webrouter.${LAIN_DOMAIN}/ab_admin?action=policygroup_check -d '{"1":{"divtype":"uidsuffix","divdata":[{"suffix":"1","upstream":"beta1"}]},"2":{"divtype":"iprange","divdata":[{"range":{"start":1111,"end":2222},"upstream":"beta1"}]}}'
{"desc":"success ","code":200}
curl webrouter.${LAIN_DOMAIN}/ab_admin?action=policygroup_set -d '{"1":{"divtype":"uidsuffix","divdata":[{"suffix":"1","upstream":"beta1"}]},"2":{"divtype":"iprange","divdata":[{"range":{"start":1111,"end":2222},"upstream":"beta1"}]}}'
{"data":{"group":[5,6],"groupid":0},"desc":"success ","code":200}
curl "webrouter.${LAIN_DOMAIN}/ab_admin?action=policygroup_get&policygroupid=0"
{"data":{"group":["5","6"],"groupid":0},"desc":"success ","code":200}
curl "webrouter.${LAIN_DOMAIN}/ab_admin?action=policygroup_del&policygroupid=0"
{"desc":"success ","code":200}

curl "webrouter.${LAIN_DOMAIN}/ab_admin?action=runtime_set&hostname=test.${LAIN_DOMAIN}&policygroupid=0"
{"desc":"success ","code":200}
curl "webrouter.${LAIN_DOMAIN}/ab_admin?action=runtime_get&hostname=test.${LAIN_DOMAIN}"
{"data":{"divsteps":2,"runtimegroup":{"second":{"divModulename":"abtesting.diversion.iprange","userInfoModulename":"abtesting.userinfo.ipParser","divDataKey":"ab:policies:6:divdata"},"first":{"divModulename":"abtesting.diversion.uidsuffix","userInfoModulename":"abtesting.userinfo.uidParser","divDataKey":"ab:policies:5:divdata"}}},"desc":"success ","code":200}
curl "webrouter.${LAIN_DOMAIN}/ab_admin?action=runtime_del&hostname=test.${LAIN_DOMAIN}"
{"desc":"success ","code":200}
```
