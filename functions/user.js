export async function onRequestPost(context) {
	
	return Response.redirect(new URL(context.request.url).origin + '/', 302);
}