# Nashhal Trust Web3

طبقة توثيق اختيارية تسجل بصمة سجل الأخبار على Ethereum Sepolia وتربطها بملف أرشيف على IPFS.

Ethereum توضح أن Sepolia هي شبكة الاختبار العامة المخصصة لاختبار التطبيقات والعقود. citeturn149609search9

لا يوضع نص الخبر أو الصور أو البيانات الخاصة على البلوكشين. ملف manifest يحتوي على معرفات الأخبار وبصماتها فقط. IPFS يستخدم عناوين محتوى تعتمد على التشفير، وأي تغيير في المحتوى يؤدي إلى CID مختلف. citeturn114595search0turn149609search0

## إعداد الأسرار

- WEB3_RPC_URL
- WEB3_PRIVATE_KEY
- WEB3_CONTRACT_ADDRESS
- IPFS_API_URL (اختياري)
- IPFS_API_TOKEN (اختياري)

عند غياب إعدادات Web3، ينتج النظام سجل prepared ولا يؤثر ذلك على نشر الأخبار.