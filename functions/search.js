export async function onRequestGet(context) {
	
	return Response.redirect(new URL(context.request.url).origin + '/', 302);
}